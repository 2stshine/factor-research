"""Independent SQL formula tests; the fake PG wire is NOT live PG validation."""
from contextlib import contextmanager
from types import SimpleNamespace
import math
import sqlite3

import numpy as np
import pandas as pd
import pytest

from engine import reference_expansion_parity as parity
from engine import reference_expansion_formulas as financial
from engine import reference_price_expansion as price
from engine import reference_gold as gold
from engine.research_generation import digest
from engine.reference_library import definition_hash


ALL_REFS=sorted(parity.REFERENCES)


def panel(assets=(1,2),months=42):
    dates=pd.date_range("2015-01-31",periods=months,freq="ME")
    rows=[]
    all_numeric=parity.required_columns(ALL_REFS)
    for asset in assets:
        for month,date in enumerate(dates):
            row={col:100.+i*3+month+asset for i,col in enumerate(all_numeric)}
            row.update(asset_id=str(asset),stock_code=f"{asset:05d}0",date=date,
                       known_at=date.tz_localize("Asia/Seoul")+pd.Timedelta(hours=16),market="KOSPI")
            row.update(adj_close=100*1.01**month,nominal_close=1000*1.01**month,
                market_cap=1e10*(1+month/100),share_turnover_1m=.02,share_turnover_cv_1m=.3,
                mean_traded_value_1m=1e7+month,traded_value_cv_1m=.4,zero_volume_fraction_1m=.1,
                downside_semideviation_252d=.01,return_skew_252d=-.7,parkinson_variance_1m=.0003,
                overnight_return_1m=.07,intraday_return_1m=-.06,positive_return_days_1m=12.,negative_return_days_1m=6.,
                daily_return_observations_252d=252.)
            row.update({column:20. for column in price.COUNT_COLUMNS})
            rows.append(row)
    return pd.DataFrame(rows)


def calculated(frame,refs=ALL_REFS):
    parts=[]
    for ref in refs:
        raw=price.calculate(frame,ref) if ref in price.REFERENCE_SPECS else financial.calculate(frame,ref)
        valid=raw.notna()
        part=frame.loc[valid,["asset_id","stock_code","date","known_at"]].copy()
        part["reference_id"],part["definition_hash"],part["value"]=ref,"a"*64,raw.loc[valid]
        parts.append(part)
    return pd.concat(parts,ignore_index=True)


@pytest.mark.parametrize("reference_id",ALL_REFS)
def test_all_38_sql_formulas_match_independent_python_estimators(reference_id):
    frame=panel()
    values=calculated(frame,[reference_id])
    result=parity.validate_sqlite(frame,values,reference_ids=[reference_id])
    assert result["passed"] and result["rows_compared"]==len(values)>0


def test_all_38_combined_query_and_stock_code_identity():
    frame=panel()
    values=calculated(frame)
    assert len(parity.REFERENCES)==38
    result=parity.validate_sqlite(frame,values)
    assert result["rows_compared"]==len(values)
    broken=values.copy()
    broken.loc[0,"stock_code"]="999990"
    with pytest.raises(ValueError,match="parity failed"):
        parity.validate_sqlite(frame,broken)


@pytest.mark.parametrize("missing_month",[1,12,15,28,35])
def test_sparse_calendar_matches_true_month_ranges_not_row_lags(missing_month):
    frame=panel(months=55)
    deleted=frame.index[frame.asset_id.eq("1")][missing_month]
    frame=frame.drop(deleted)
    ids=["kr_information_discreteness_12_2_v1","kr_reversal_36_13_price_v1"]
    values=calculated(frame,ids)
    result=parity.validate_sqlite(frame,values,reference_ids=ids)
    assert result["rows_compared"]==len(values)
    # Missing a recent month need not invalidate a long reversal whose entire
    # 36..13-month measurement window is earlier than that missing month.
    if missing_month==35:
        output=values[values.reference_id.eq(ids[1]) & values.asset_id.eq("1")]
        assert output.date.eq(pd.Timestamp("2018-01-31")).any()


def test_sparse_calendar_with_zero_negative_missing_price_and_impossible_counts():
    frame=panel(months=60)
    frame.loc[3,"adj_close"]=0
    frame.loc[10,"adj_close"]=-1
    frame.loc[22,"adj_close"]=np.nan
    frame.loc[27,"positive_return_days_1m"]=30
    frame.loc[32,"negative_return_days_1m"]=.5
    frame.loc[40,"price_return_observations_1m"]=14
    ids=["kr_information_discreteness_12_2_v1","kr_reversal_36_13_price_v1"]
    assert parity.validate_sqlite(frame,calculated(frame,ids),reference_ids=ids)["passed"]


def test_invalid_counts_domains_nonfinite_accounts_and_signed_numerators():
    frame=panel(months=42)
    for i,col in enumerate(parity.required_columns(ALL_REFS)):
        frame.loc[(i*3)%len(frame),col]=np.nan
        frame.loc[(i*3+1)%len(frame),col]=np.inf
        frame.loc[(i*3+2)%len(frame),col]=-1.
    frame.loc[12,"turnover_observations_1m"]=20.5
    frame.loc[13,"daily_return_observations_252d"]=253.
    frame.loc[14,"overnight_observations_1m"]=19.
    frame.loc[15,"intraday_return_1m"]=-1.
    frame.loc[16,"zero_volume_fraction_1m"]=1.01
    frame.loc[17,"fy_net_income"]=-100.
    assert parity.validate_sqlite(frame,calculated(frame))["passed"]


@pytest.mark.parametrize("change",["extra","missing","wrong_value","duplicate","nonfinite"])
def test_output_corruption_or_dropped_rows_fails_full_comparison(change):
    frame=panel()
    values=calculated(frame,["kr_roa_fy_v1"])
    if change=="extra":
        extra=values.iloc[:1].copy();extra.asset_id="99999";extra.stock_code="999990"
        values=pd.concat([values,extra],ignore_index=True)
    elif change=="missing":values=values.iloc[1:]
    elif change=="wrong_value":values.loc[0,"value"]+=.1
    elif change=="duplicate":values=pd.concat([values,values.iloc[:1]],ignore_index=True)
    else:values.loc[0,"value"]=np.inf
    with pytest.raises(ValueError):parity.validate_sqlite(frame,values)


@pytest.mark.parametrize("ids,dialect",[([],"sqlite"),(["no_such_ref"],"sqlite"),(["kr_roa_fy_v1"]*2,"postgres"),
                                        (["kr_roa_fy_v1"],"mysql"),(["x'; DROP TABLE reference_input;--"],"sqlite")])
def test_sql_builder_rejects_unknown_duplicate_or_injected_input(ids,dialect):
    with pytest.raises(ValueError):parity.sql_for(ids,dialect)


def test_sql_has_only_declared_calculations_and_calendar_windows():
    sql=parity.sql_for(ALL_REFS,"postgres")
    assert "FROM reference_input" in sql
    assert "RANGE BETWEEN 36 PRECEDING AND 12 PRECEDING" in sql
    assert "RANGE BETWEEN 11 PRECEDING AND 1 PRECEDING" in sql
    assert "lag(" not in sql and "following" not in sql.lower()
    assert "gold." not in sql and "fwd_" not in sql and "total_return" not in sql


class FakePostgresTransport:
    """Exercises staging/sample/cleanup wiring in SQLite, not PostgreSQL proof."""
    def __init__(self):
        self.db=sqlite3.connect(":memory:")
        self.db.create_function("ln",1,lambda v:math.log(v) if v is not None and v>0 else None)
        self.db.create_function("floor",1,lambda v:math.floor(v) if v is not None else None)
        self.commands=[];self.staged=[];self.copied_this_call=[]
    @contextmanager
    def transaction(self):
        try:yield self
        except Exception:
            self.db.rollback()
            raise
        else:self.db.commit()
    def cursor(self):return FakeCursor(self)


class FakeCursor:
    def __init__(self,owner):self.owner=owner;self.result=None
    def __enter__(self):return self
    def __exit__(self,*_):return False
    def execute(self,sql):
        self.owner.commands.append(sql)
        if sql.startswith("SET LOCAL"):return
        if sql.startswith("CREATE TEMP TABLE"):
            self.owner.copied_this_call=[]
        sql=sql.replace(" ON COMMIT DROP","").replace("pg_temp.reference_input","reference_input")
        self.result=self.owner.db.execute(sql)
    @property
    def description(self):return [SimpleNamespace(name=d[0]) for d in self.result.description]
    def fetchall(self):return self.result.fetchall()
    @contextmanager
    def copy(self,sql):
        assert sql=="COPY reference_input FROM STDIN"
        yield self
        self.owner.staged.append(list(self.owner.copied_this_call))
    def write_row(self,row):
        self.owner.copied_this_call.append(row)
        self.owner.db.execute("INSERT INTO reference_input VALUES("+",".join("?" for _ in row)+")",row)


def test_fixed_sample_comes_from_output_assets_and_keeps_all_history_and_rows():
    assets=[1,2,3,4,5,6,7,8,9,10,11,50,99,100,1000]
    frame=panel(assets=assets,months=42)
    frame.loc[frame.asset_id.eq("1000"),"nominal_close"]=np.nan
    ids=["kr_nominal_price_v1","kr_reversal_36_13_price_v1"]
    # Entirely invalid asset excluded from valid output, yet stays input.
    frame.loc[frame.asset_id.eq("1000"),"adj_close"]=np.nan
    values=calculated(frame,ids)
    conn=FakePostgresTransport()
    result=parity.validate_parity(frame,values,conn)
    valid=assets[:-1]
    expected=sorted({valid[(len(valid)-1)*i//9] for i in range(10)})
    assert result["postgres_sample"]["asset_ids"]==expected
    assert set(int(row[0]) for row in conn.staged[0])==set(expected)
    assert len(conn.staged[0])==42*len(expected)
    canonical=gold.canonical_values(values)
    selected=[row for row in canonical if row["asset_id"] in expected]
    assert result["values_sha256"]==digest(canonical)
    assert result["postgres_sample"]["values_sha256"]==digest(selected)
    assert result["postgres_sample"]["rows_compared"]==len(selected)
    assert result["postgres_sample"]["selection"]==parity.SELECTION
    assert result["kind"]=="INDEPENDENT_SQLITE_FULL_POSTGRES_FIXED_SAMPLE"
    assert result["sql_sha256"]==result["sqlite_full"]["sql_sha256"]
    assert result["rtol"]==result["postgres_sample"]["rtol"]==result["sqlite_full"]["rtol"]==1e-10
    assert result["atol"]==0


def test_multiple_bounded_groups_do_not_leave_temp_tables():
    frame=panel()
    conn=FakePostgresTransport()
    for refs in [["kr_roa_fy_v1"],["kr_information_discreteness_12_2_v1"],["kr_reversal_36_13_price_v1"]]:
        assert parity.validate_parity(frame,calculated(frame,refs),conn)["passed"]
        assert not conn.db.execute("SELECT name FROM sqlite_temp_master WHERE name='reference_input'").fetchall()
    assert sum(command=="DROP TABLE pg_temp.reference_input" for command in conn.commands)==3


def test_parity_payload_satisfies_existing_gold_full_sample_contract():
    # Synthetic metadata/transport is used solely to exercise the consistency
    # contract. No source has actually been certified and no DB is written.
    from engine.reference_library_v2 import SOURCE_TYPE,SOURCE_CONTRACT,PIT_STATUS
    ref="kr_nominal_price_v1"
    definition={"id":ref,"name_ko":"소프트웨어 테스트","family":"TEST_ONLY", "object_type":"STOCK_CHARACTERISTIC",
        "role":"MEASUREMENT_CONTROL","alpha_approved":False,"formula":price.REFERENCE_SPECS[ref]["formula"],
        "orientation":-1,"required_columns":["nominal_close"],"sources":[{"url":"https://example.invalid/software-fixture"}],
        "adaptation":"SOFTWARE_TEST_ONLY_NOT_MARKET_EVIDENCE","lookback":{},
        "readiness":{"status":"IMPLEMENTED_REQUIRES_ATTESTATION","blockers":[]}}
    frame=panel(assets=(1,2,3,4,5,6,7,8,9,10,11,12),months=2)
    values=calculated(frame,[ref]);values["definition_hash"]=definition_hash(definition)
    checked=parity.validate_parity(frame,values,FakePostgresTransport())
    attestation={"status":"CERTIFIED","source_type":SOURCE_TYPE,"source_contract":SOURCE_CONTRACT,
        "source_version":"b"*64,"evidence_sha256":"b"*64,"input_sha256":"a"*64,"pit_status":PIT_STATUS,
        "first_vintage_independently_verified":False,"identity_contract":"HISTORICAL_ASSET_ID","scope":"KRX_COMMON_STOCK"}
    validation={"value_rows":len(values),"source_version":"b"*64,"input_sha256":"a"*64,
        "source_evidence_sha256":"b"*64,"role":"MEASUREMENT_CONTROL","alpha_approved":False,"implementation_sha256":"c"*64,
        "references":[{"reference_id":ref,"definition_hash":definition_hash(definition),
                       "value_rows":len(values),"status":"MEASUREMENT_VALIDATED"}]}
    publication,rows=gold.build_publication(values,[definition],attestation=attestation,validation=validation,parity=checked)
    assert gold.validate_publication(publication,rows)==publication


def test_postgres_failure_never_turns_sqlite_only_into_publication_parity():
    class Offline:
        def transaction(self):raise ConnectionError("No actual PG connection")
    frame=panel()
    with pytest.raises(ConnectionError):
        parity.validate_parity(frame,calculated(frame,["kr_roa_fy_v1"]),Offline())


@pytest.mark.parametrize("bad",["duplicate","nonmonthend","unsafe_ticker","numeric_string","month_index"])
def test_invalid_staging_panel_fails_before_any_pg_call(bad):
    frame=panel()
    values=calculated(frame,["kr_roa_fy_v1"])
    if bad=="duplicate":frame=pd.concat([frame,frame.iloc[:1]])
    elif bad=="nonmonthend":frame.loc[0,"date"]=pd.Timestamp("2015-01-30")
    elif bad=="unsafe_ticker":frame.loc[0,"stock_code"]="5930"
    elif bad=="numeric_string":frame.fy_total_assets=frame.fy_total_assets.astype(str)
    else:frame["month_index"]=1
    conn=FakePostgresTransport()
    with pytest.raises(ValueError):parity.validate_parity(frame,values,conn)
    assert not conn.commands
