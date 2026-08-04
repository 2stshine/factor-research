"""가격 패널 + T1 유니버스 계약.

T1 은 게이트의 심장이다 — 레드팀 공격 18개 중 11개가 여기서 죽었다.
핵심 원칙: **유니버스는 게이트가 고정하고 팩터가 바꿀 수 없다.**
팩터 정의에 유니버스 마스킹이 들어가면 retention 같은 비율 기준을 분모 파괴로 무력화할 수 있다.
"""
from __future__ import annotations

import glob
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# T1.1 유니버스 계약 — 실측 기준(2026-07-07): 전체 2,873 → 최종 2,486
MIN_LISTING_DAYS = 250          # 상장 후 경과 거래일
SUPPORTED_MARKETS = ("KOSPI", "KOSDAQ")   # KONEX 는 Silver 에서 이미 제외됨
MARKET_NORM = {"KOSDAQ GLOBAL": "KOSDAQ"}
INVESTABLE_ADV = 5e8            # 투자가능 유니버스 하한(20일 평균 거래대금)

MARCAP_COLS = ["Code", "Name", "Date", "Close", "Changes", "Volume", "Amount",
               "Marcap", "Stocks", "Market", "Dept"]


@dataclass
class Panel:
    """월말 패널. 팩터 계산과 게이트가 공유하는 단일 진실."""
    monthly: pd.DataFrame              # 월말 스냅샷
    dead: pd.Series                    # 상장폐지 종목 → 마지막 거래일
    meta: dict = field(default_factory=dict)

    @property
    def universe(self) -> pd.Series:
        d = self.monthly
        return d["in_universe"] & d["market_cap"].notna() & (d["market_cap"] > 0)

    @property
    def investable(self) -> pd.Series:
        return self.universe & (self.monthly["adv20"] >= INVESTABLE_ADV)


def _adj_close(m: pd.DataFrame) -> pd.Series:
    """KRX 전일대비가 조정기준이라는 성질로 수정종가 역산.

    일별계수 k = (close − 전일대비) / 직전 close  (평일 1, 분할·병합일 조정비율)
    adj_close = close × C_last / C,  C = k 의 누적곱.
    """
    prev = m.groupby("Code")["Close"].shift(1)
    adj_prev = m["Close"] - m["Changes"].fillna(0)
    k = np.where((prev > 0) & (adj_prev > 0), adj_prev / prev, 1.0)
    k = np.where(np.abs(k - 1) < 1e-9, 1.0, k)   # 정상일 정수라 부동소수 잡음 제거
    C = pd.Series(k, index=m.index).groupby(m["Code"]).cumprod()
    C_last = C.groupby(m["Code"]).transform("last")
    return m["Close"] * (C_last / C)


def build(bronze_dir: str, *, verbose: bool = True) -> Panel:
    """bronze marcap → 월말 패널 + T1 유니버스."""
    files = sorted(glob.glob(f"{bronze_dir}/stock/marcap/date=*/all.parquet"))
    if not files:
        raise FileNotFoundError(f"marcap 파케이 없음: {bronze_dir}/stock/marcap/")
    if verbose:
        print(f"[panel] marcap {len(files):,}일 로딩...", flush=True)

    m = pd.concat([pd.read_parquet(f, columns=MARCAP_COLS) for f in files], ignore_index=True)
    m["Code"] = m["Code"].astype(str)
    m["trade_date"] = pd.to_datetime(m["Date"])
    m["Market"] = m["Market"].replace(MARKET_NORM)
    m = m.sort_values(["Code", "trade_date"]).reset_index(drop=True)
    m["adj_close"] = _adj_close(m)

    # ---- T1.1 유니버스 계약 (팩터가 바꿀 수 없음) ----
    dept = m["Dept"].fillna("").astype(str)
    name = m["Name"].fillna("").astype(str)
    m["ok_market"] = m["Market"].isin(SUPPORTED_MARKETS)
    m["ok_common"] = m["Code"].str.endswith("0")            # 보통주만 (우선주 제외)
    m["is_spac"] = dept.str.contains("SPAC", case=False) | name.str.contains("스팩")
    m["is_reit"] = name.str.contains("리츠")
    # 상장연령 — cumcount 는 '데이터 시작일부터'를 세므로 그대로 쓰면 안 된다.
    # 2015-01-02 에 이미 존재하던 종목(삼성전자 등)이 전부 '신규상장'으로 취급돼
    # 첫 1년이 통째로 배제된다(실측: 2015년 유니버스 0종목 = 표본의 9% 증발).
    # 데이터 시작일에 있던 종목은 상장일을 알 수 없으므로 기성 종목으로 간주한다.
    data_start = m["trade_date"].min()
    first_seen = m.groupby("Code")["trade_date"].transform("min")
    m["age_days"] = m.groupby("Code").cumcount() + 1
    m["seasoned"] = first_seen <= data_start
    m["ok_age"] = (m["age_days"] >= MIN_LISTING_DAYS) | m["seasoned"]
    # T1.3 부실 플래그 — 배제가 아니라 라벨 (상장폐지 사유 근사에 사용)
    m["is_distress"] = dept.str.contains("관리종목|투자주의환기", regex=True)
    m["in_universe"] = (m["ok_market"] & m["ok_common"]
                        & ~m["is_spac"] & ~m["is_reit"] & m["ok_age"])

    # ---- T1.2 상장폐지 탐지 ----
    last_day = m["trade_date"].max()
    last_seen = m.groupby("Code")["trade_date"].max()
    dead = last_seen[last_seen < last_day - pd.Timedelta(days=20)]

    # ---- 월말 스냅샷 + 유동성 ----
    m["adv20"] = m.groupby("Code")["Amount"].transform(
        lambda s: s.rolling(20, min_periods=5).mean())
    m["ym"] = m["trade_date"].dt.to_period("M")
    idx = m.groupby(["Code", "ym"])["trade_date"].idxmax()
    keep = ["Code", "Name", "ym", "trade_date", "adj_close", "Close", "Marcap",
            "Stocks", "Amount", "adv20", "Market", "in_universe", "is_distress", "age_days"]
    me = (m.loc[idx, keep]
            .rename(columns={"Marcap": "market_cap", "Amount": "amount"})
            .sort_values(["Code", "ym"]).reset_index(drop=True))

    meta = {"n_files": len(files), "last_day": last_day,
            "n_dead": len(dead), "n_stocks": m["Code"].nunique()}
    if verbose:
        snap = me[me["ym"] == me["ym"].max()]
        print(f"[panel] {len(me):,}행 / {me['ym'].nunique()}개월 / "
              f"최종 유니버스 {int(snap['in_universe'].sum()):,}종목 / 상장폐지 {len(dead):,}종목")
    return Panel(monthly=me, dead=dead, meta=meta)


def forward_returns(panel: Panel, terminal: float = -0.50) -> pd.Series:
    """다음 달 수익률. T1.2 — 상장폐지 종목의 마지막 관측에 종착수익률을 강제 부여.

    이걸 안 하면 롱레그의 최악 실현값이 표본에서 조용히 증발한다(NaN → 횡단면 제외).
    게이트는 terminal ∈ {0.0, -0.50, -1.00} 3점 스트레스를 요구한다.
    """
    d = panel.monthly.sort_values(["Code", "ym"])
    fwd = d.groupby("Code")["adj_close"].shift(-1) / d["adj_close"] - 1
    last_ym = d["ym"].max()
    is_last = (d["ym"] == d.groupby("Code")["ym"].transform("max")) & (d["ym"] != last_ym)
    # 원본 인덱스로 되돌려 반환한다 — 호출부가 .values 로 위치대입하면 정렬이 어긋난 순간
    # 미래수익률이 다른 종목 행에 조용히 붙는다(에러도 NaN 도 안 난다).
    return pd.Series(np.where(is_last, terminal, fwd),
                     index=d.index).reindex(panel.monthly.index)
