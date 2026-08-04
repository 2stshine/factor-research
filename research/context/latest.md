# Factor research context

> 다음 연구 루프는 전략을 만들기 전에 이 파일을 읽어야 한다.

## Frozen research state

- Silver source: `RDS public Silver`
- Silver data period: `2015-01` ~ `2026-08`
- Common evaluation period: `2018-03` ~ `2026-08`
- Rows/months/assets: `334,354` / `140` / `3,301`
- Return field: `total_return_close`
- Gate ruleset: `fr-3.1.0`
- Recorded autonomous cycles: `12`

## Available strategy inputs

| column | overall coverage | latest-month coverage |
|---|---:|---:|
| `adv20` | 100.0% | 100.0% |
| `market` | 100.0% | 100.0% |
| `market_cap` | 100.0% | 100.0% |
| `net_income_ttm` | 70.7% | 90.6% |
| `operating_income_ttm` | 70.7% | 90.7% |
| `return_close` | 100.0% | 100.0% |
| `revenue_ttm` | 69.3% | 87.9% |
| `shares` | 100.0% | 100.0% |
| `sue_score` | 59.2% | 86.0% |
| `total_assets` | 82.6% | 95.5% |
| `total_equity` | 82.6% | 95.5% |
| `total_liabilities` | 82.6% | 95.5% |
| `trading_value` | 100.0% | 100.0% |

## Registered factors

| factor | category | family | definition hash | hypothesis |
|---|---|---|---|---|
| `value_bp` | value | `value_bp` | `fd04cd8318be381d` | 장부가 대비 저평가된 주식은 위험보상 또는 과잉반응 교정으로 초과수익을 낸다 (Fama-French 1992). 한국은 지주·금융 비중이 커 섹터 편향 주의. |
| `value_ep` | value | `value_ep` | `0f96f2514e3c7a56` | 이익 대비 저평가. B/P 와 달리 수익성이 반영돼 가치함정을 덜 만든다. 실측상 quality 군과 ρ=0.91 로 사실상 수익성 팩터에 가깝다. |
| `value_sp` | value | `value_sp` | `3d5060d0124f4605` | 매출 대비 저평가. 적자 기업에서도 정의되어 E/P 의 결측을 보완한다. |
| `qual_roe` | quality | `qual_roe` | `8428891b185a9db5` | 자기자본이익률이 높은 기업은 이익 지속성이 높고 시장이 그 지속성을 과소평가한다 (Novy-Marx 2013 의 수익성 팩터 계열). ⚠️ 섹터 중립화 미검정 — 고ROE 가 특정 업종에 쏠려 있으면 섹터 베팅일 수 있다. |
| `qual_opm` | quality | `qual_opm` | `d452ffb71dae9ee7` | 영업이익률이 높으면 가격결정력·비용구조 우위가 있고 이익의 질이 높다. ROE 와 ρ=0.96 이라 T5.1 직교성에서 둘 중 하나만 남는다. |
| `qual_lev` | quality | `qual_lev` | `551f0498e0cb6f6b` | 부채비율이 낮으면 재무위험이 낮아 부실 시 손실을 피한다. 실측 t=0.48 로 한국에서는 무의미했다 — 기록용으로 유지. |
| `mom_12_1` | momentum | `mom_12_1` | `52aac900f2d206fe` | 과거 승자가 계속 이긴다(Jegadeesh-Titman 1993). ⚠️ 한국 실측은 t=−1.34 로 **부호가 반대** — 미국식 템플릿이 그대로 안 통한다. |
| `rev_1m` | momentum | `rev_1m` | `5d85c305ea247c91` | 1개월 단기 반전 — 유동성 공급 보상(Lehmann 1990). ⚠️ IC t=4.05 로 강하지만 롱온리 순알파 −7.64%. IC 는 숏레그·마이크로캡이 만든 것. |
| `size` | size | `size` | `c261f8d2dedeb948` | 소형주 프리미엄. ⚠️ 실측상 전체 유니버스 t=0.75 인데 투자가능 유니버스에서 부호가 뒤집힌다(t=−4.39) — 유동성 없는 종목이 만든 착시. |
| `sue` | earnings | `sue` | `f7f1108e12dbb19a` | 계절 랜덤워크 기대 대비 실적 서프라이즈가 이후 수익률로 이어진다(PEAD; Bernard-Thomas 1989). 컨센서스 없이 시계열만으로 구성 가능하고 애널리스트 미커버 소형주까지 잡는다. 실측상 모든 팩터와 \|ρ\|≤0.36 으로 가장 독립적. |
| `asset_turnover` | quality | `asset_turnover` | `413015db39ae3e23` | 총자산 대비 매출이 높으면 자산을 효율적으로 굴리는 기업이고, 시장은 이 효율성의 지속성을 과소평가한다. 순이익 기반 지표보다 회계 조작에 덜 노출된다(Novy-Marx 2013 계열). |
| `asset_growth_12m` | other | `asset_growth` | `8036ceaacef6ac62` | 최근 12개월 총자산 증가율이 낮은 기업은 과잉투자와 제국 확장에 따른 가치 훼손을 덜 겪어 이후 롱온리 초과수익을 낸다. |
| `defensive_small_value` | value | `small_value` | `5ca0936652af719a` | 저평가·소형·저변동 특성이 동시에 있는 종목은 정보 비대칭에 따른 가격 오류를 보유하면서 취약하고 투자 불가능한 소형주를 줄여 이후 안정적인 롱온리 초과수익을 낸다. |
| `defensive_value` | value | `defensive_value` | `89e8c8685bac02ac` | 장부가치 대비 저평가되면서 최근 12개월 가격 변동성이 낮은 종목은 고변동 가치함정을 피하면서 가치 프리미엄을 보존해 이후 롱온리 초과수익을 낸다. |
| `downside_vol_12m` | other | `low_volatility` | `57a4463adb3b9ee7` | 최근 12개월 손실 구간의 하방 변동성이 낮은 종목은 재무적 취약성과 복권형 하락위험이 과대평가된 종목을 피하면서 상승 변동성은 보존해 이후 롱온리 초과수익을 낸다. |
| `earnings_confirmed_small_value` | earnings | `catalyst_small_value` | `89e7b296449ec6b2` | 저평가된 소형주 중 표준화 이익 서프라이즈가 높은 종목은 실적 촉매가 가격 오류의 교정을 촉진하여 이후에도 상대적으로 높은 수익을 낸다. |
| `high_12m_proximity` | momentum | `price_anchoring` | `5bc5c56e28ba5b4f` | 최근 12개월 월말 고점에 가까운 종목은 투자자의 고점 앵커링으로 긍정적 정보가 천천히 반영되어 이후에도 상대적으로 높은 수익을 낸다. |
| `low_vol_12m` | other | `low_volatility` | `ae41d1ec7120cde0` | 최근 12개월 변동성이 낮은 종목은 레버리지 제약과 투자자의 복권형 고변동 주식 선호 때문에 과소평가되어 이후 롱온리 초과수익을 낸다. |
| `operating_roa` | quality | `operating_roa` | `0c399c65bc5c8e11` | 총자산 대비 최근 12개월 영업이익이 높은 기업은 자산을 지속적으로 효율적으로 활용하며, 시장이 이 영업 수익성의 지속성을 과소평가해 이후 상대적으로 높은 수익을 낸다. |
| `profitable_small_value` | quality | `quality_small_value` | `ec639be0f12aad5a` | 저평가된 소형주 중 총자산 대비 영업이익이 높은 기업은 가격 오류와 지속 가능한 영업성과를 동시에 보유해 이후에도 상대적으로 높은 수익을 낸다. |
| `quality_stability` | quality | `quality_stability` | `c4315c8db6ef4e63` | 영업수익성·자산효율·자기자본 완충력이 높고 가격 변동성이 낮은 기업은 지속 가능한 사업 품질이 과소평가되어 이후에도 안정적인 초과수익을 낸다. |
| `small_value` | value | `small_value` | `764fa5bbc3b80dc4` | 장부가치 대비 저평가된 소형주는 기관 미커버와 높은 정보비대칭 때문에 가격 오류가 더 천천히 교정되어 투자 가능한 범위에서도 이후 롱온리 초과수익을 낸다. |
| `solvent_value` | value | `defensive_value` | `fb56009a013e76e1` | 장부가치 대비 저평가되면서 부채/자기자본 비율이 낮은 종목은 재무적 가치함정을 피하고 하방 손실을 줄여 이후 안정적인 롱온리 초과수익을 낸다. |

## Prior autonomous cycles

| cycle | factor | verdict | key result | failed checks | strongest relation |
|---|---|---|---|---|---|
| `cycle-0001-low_vol_12m` | `low_vol_12m` | REJECT | net=1.05%, IR=0.16 | 실비용 순알파, net_IR | value_bp (0.35) |
| `cycle-0002-asset_growth_12m` | `asset_growth_12m` | REJECT | IC 계산 전 조기종료 | 월별 커버리지 하위10%, 종착수익률 3점 방향 | qual_roe (-0.35) |
| `cycle-0003-downside_vol_12m` | `downside_vol_12m` | REJECT | net=0.38%, IR=0.06 | 실비용 순알파, net_IR | value_ep (0.37) |
| `cycle-0004-defensive_value` | `defensive_value` | REJECT | net=3.09%, IR=0.47 | net_IR | value_bp (0.83) |
| `cycle-0005-solvent_value` | `solvent_value` | REJECT | net=1.69%, IR=0.37 | 실비용 순알파, net_IR | value_bp (0.67) |
| `cycle-0006-small_value` | `small_value` | REJECT | net=7.54%, IR=1.06 | 투자가능 IC 유지율 | value_bp (0.78) |
| `cycle-0007-defensive_small_value` | `defensive_small_value` | REJECT | net=5.18%, IR=0.78 | 섹터 중립화 가능, 고정 OOS, Deflated Sharpe, 다중검정 FDR | defensive_value (0.87) |
| `cycle-0008-high_12m_proximity` | `high_12m_proximity` | REJECT | net=1.10%, IR=0.14 | 투자가능 IC 유지율, 투자가능 IC HAC 유의성, 실비용 순알파, net_IR | downside_vol_12m (0.68) |
| `cycle-0009-earnings_confirmed_small_value` | `earnings_confirmed_small_value` | REJECT | net=7.94%, IR=1.11 | 섹터 중립화 가능, 고정 OOS, Deflated Sharpe, 다중검정 FDR | small_value (0.81) |
| `cycle-0010-quality_stability` | `quality_stability` | REJECT | net=3.18%, IR=0.54 | net_IR | qual_roe (0.67) |
| `cycle-0011-profitable_small_value` | `profitable_small_value` | REJECT | net=6.21%, IR=0.96 | 레짐 집중도, 섹터 중립화 가능, 고정 OOS, Deflated Sharpe, 다중검정 FDR | small_value (0.78) |
| `cycle-0012-operating_roa` | `operating_roa` | PROVISIONAL | IC=0.069, OOS IC=0.101 | 섹터 중립화 가능 | qual_opm (0.92) |

## Next-loop constraints

- 기존 definition hash를 재시험하지 않는다.
- 결과를 보기 전에 가설·메커니즘·반증 기준과 전략 파일을 먼저 고정한다.
- 실패한 정의를 덮어쓰지 않는다. 수정 아이디어는 새 이름 또는 새 버전 파일로 등록한다.
- 게이트, 패널, 비용모형, OOS 시작점과 기존 결과를 후보에 유리하게 수정하지 않는다.
- 한 루프에서는 후보 하나만 새로 만든다.
- 후보 하나는 단일 경제 신호만 사용한다. 여러 팩터의 순위·점수를 가중합하지 않는다.
- 수익률·IR은 진단값이며 승격 판정은 무결성·IC 최소요건·IC 강건성으로 한다.
- `publish --apply`를 실행하지 않는다.
