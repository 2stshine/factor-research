"""Record actual source searches and bounded consensus evidence limitations."""
from pathlib import Path
from engine import research_data_sources as ds
from scripts.publish_reference_expansion import save_json,sha,load_json

ROOT=Path('output/phenomena/reference-new-information-20261003')
SOURCES=[
 dict(source_id='kis_owned',title='Certified KIS investor and short-sale observations',provider='KIS',market='KRX',frequency='daily',
      variables=['foreign_net_buy','institution_net_buy','short_volume'],pit_status='assumed',format='json',
      description='Existing RDS public.kis_market_observation, venue J; policy time next-day 08:30 KST; historical revisions possible.'),
 dict(source_id='dart_employee',title='OpenDART employee disclosure',provider='FSS OpenDART',market='KRX',frequency='annual',
      variables=['employees'],pit_status='assumed',format='json',url='https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS002&apiId=2019011',
      description='Official employee endpoint; response includes receipt and statement date. Certified FY receipt identity bridge required.'),
 dict(source_id='fmp_rd',title='FMP research expense in annual income statements',provider='FMP',market='KRX',frequency='annual',
      variables=['rd_expense'],pit_status='assumed',format='json',url='https://site.financialmodelingprep.com/developer/docs/stable/income-statement',
      description='Existing Ultimate access. Ignore provider filingDate; bridge consolidated revenue and receipt against DART.'),
 dict(source_id='fmp_consensus_current',title='FMP annual analyst estimates probe',provider='FMP',market='KRX',frequency='annual',
      variables=['eps_mean'],pit_status='unverified',format='json',url='https://site.financialmodelingprep.com/developer/docs/stable/financial-estimates',
      description='Five Korean probes return target-year estimates without snapshot/as-of revision timestamp. Not historical consensus input.'),
]

def run():
 save_json(ROOT/'discovery-source-catalog.json',SOURCES)
 specifications=[
  ('owned-flows-20261003','flow', 'daily',['foreign_net_buy','institution_net_buy','short_volume'],
   '투자자별 매수 압력과 공매도 거래가 기존 가격 측정과 다른 현상을 설명하는가',
   '가격 모멘텀 설명과 투자주체 수급 설명 구분',
   'FSC short selling resumption 2025 March 31 November 2023 ban',
   [dict(title='FSC resumption and prior restrictions',url='https://www.fsc.go.kr/po010101/84216')]),
  ('employee-history-20261003','employees','annual',['employees'],
   '같은 법인의 고용 증가가 자산 투자와 다른 확장 현상을 측정하는가','고용 확대와 자산 투자 설명 구분',
   'Belo Lin Bazdresch labor hiring stock returns 2014 employee growth hiring rate denominator',
   [dict(title='Belo Lin Bazdresch 2014 JPE',url='https://www.journals.uchicago.edu/doi/abs/10.1086/674549')]),
  ('rd-expense-history-20261003','rd_expense','annual',['rd_expense'],
   '연구개발 투입을 일반 투자 및 수익성과 구분해 측정할 수 있는가','무형 혁신 투입과 유형자산 투자 구분',
   'Samsung 2025 research development expenses 37,740,392 34,998,142',
   [dict(title='Samsung official accounting research expense table',url='https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_3Q_Interim_Report.pdf')]),
  ('consensus-vintages-20261003','consensus','monthly',['eps_mean'],
   '당시 실적 예상치의 수정 방향을 실현 실적 및 사후 재작성과 구분할 수 있는가','기대 변화와 실현 실적 변화 구분',
   'FMP analyst estimates historical as of parameter snapshots API historical consensus',
   [dict(title='FMP official FAQ on analyst forecast timing',url='https://site.financialmodelingprep.com/de/faqs?code=analyst'),
    dict(title='FMP documented financial estimates endpoint',url='https://site.financialmodelingprep.com/developer/docs/stable/financial-estimates')]),
 ]
 for rid,term,freq,variables,question,distinguishes,query,results in specifications:
  case=ROOT/'data-requirements'/rid
  if case.exists():continue
  case=ds.create_requirement(ROOT/'data-requirements',dict(requirement_id=rid,question_id=rid,research_question=question,
   discriminates=distinguishes,market='KRX',frequency=freq,start_date='2015-01-01',end_date='2026-09-30',
   variables=variables,entity_column='asset_id',allow_pit_assumed=True,budget=dict(searches=6,fetches=6,bytes=20000000,elapsed_seconds=86400)))
  ds.search_catalog(case,ROOT/'discovery-source-catalog.json',term)
  ds.record_web_search(case,query,results)
  if term=='consensus':
   ds.mark_unmet(case,'Actual five-Korean-symbol FMP probes contain forecast-target dates but no historical snapshot/as-of revision timestamp. A licensed historical vintage export or documented provider endpoint is still required. This is NO_EVIDENCE, not refutation. No purchase or subscription change made.')
  save_json(case/'packet.json',ds.packet(case))
 probes=load_json(ROOT/'provider-probes/probe-receipts.json')
 consensus=[r for r in probes if r['kind']=='fmp_estimate']
 save_json(ROOT/'consensus-readiness.json',dict(status='UNMET_HISTORICAL_VINTAGE_ACCESS',gold_rows=0,
  probes=consensus,raw_probe_receipts_sha256=sha(ROOT/'provider-probes/probe-receipts.json'),
  required_fields=['asset_id','stock_code','snapshot_at','available_at','fiscal_period_end','eps_mean','analyst_count','currency','provider_snapshot_id'],
  existing_endpoint='https://financialmodelingprep.com/stable/analyst-estimates',
  inspected_public_contract='symbol, period, page, limit; returned date is forecast target period',
  provider_wide_unavailability_claim=False,question_for_user='Existing licensed FnGuide/DataGuide, QuantiWise, FactSet or LSEG historical export/access?',
  non_substitution='Target-year estimates are not silently substituted for historical consensus revisions; first observation today is not backdated.',
  prospective_seed='Raw observed snapshots retained at actual retrieval time; these do not create pre-retrieval history.'))

if __name__=='__main__':run()
