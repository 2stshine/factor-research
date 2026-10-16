(function(){'use strict';
// Presentation-only semantics over an authenticated, already released catalog.
// No candidate definitions, packets, classifications or numerical results are changed.
const COARSE_STATES=['UP_LOW','UP_HIGH','DOWN_LOW','DOWN_HIGH','UNKNOWN'];
function cycleOf(r){const n=/^cycle-(\d+)/.exec(r?.provenance?.cycle||'');return n?Number(n[1]):null;}
function campaignDay(r){const m=/^campaign-(\d{4})(\d{2})(\d{2})-\d+$/.exec(r.campaign_id||'');if(!m)return null;const day=`${m[1]}-${m[2]}-${m[3]}`,date=new Date(day+'T00:00:00Z');return Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===day?day:null;}
function chronological(records){return [...records].sort((a,b)=>{const ad=campaignDay(a),bd=campaignDay(b);if(ad===null||bd===null){if(ad!==bd)return ad===null?1:-1;}else if(ad!==bd)return bd.localeCompare(ad);return (cycleOf(b)??-1)-(cycleOf(a)??-1)||String(a.record_id).localeCompare(String(b.record_id));});}
function selectStudies(catalog){const records=chronological(catalog.records||[]),regimeStudies=records.filter(r=>r.regimes?.monthly?.length);return {latestResearch:records[0]||null,regimeStudies,selectedRegimeStudy:regimeStudies[0]||null};}
function coarseRows(g={}){
 const monthly=g.monthly||[],raw=g.regimes||[],counts=Object.fromEntries(COARSE_STATES.map(s=>[s,0]));
 for(const m of monthly){const state=m.regime||'UNKNOWN';if(!COARSE_STATES.includes(state))throw Error('Unrecognized coarse state: '+state);counts[state]++;}
 const seen=new Set();for(const r of raw){if(seen.has(r.regime)||!COARSE_STATES.includes(r.regime))throw Error('Duplicate/unrecognized coarse aggregate');seen.add(r.regime);}
 return COARSE_STATES.map(state=>{
  const stored=raw.find(r=>r.regime===state);
  if(stored){if(monthly.length&&stored.n_months!==counts[state])throw Error('Coarse aggregate/monthly count mismatch: '+state);return {...stored};}
  const n=counts[state];return {regime:state,n_months:n,n_joint_usable_months:n?null:0,n_joint_usable_episodes:n?null:0,
   support:state==='UNKNOWN'?'UNKNOWN_CONTEXT':'INSUFFICIENT_SUPPORT',rank_ic:{mean:null,ci95:null},top_minus_bottom:{mean:null,ci95:null},
   presentation_count_source:monthly.length?'RELEASED_MONTHLY_LABELS':'NO_OBSERVATIONS',aggregate_status:n?'NOT_COLLECTED':'NO_OBSERVATIONS'};
 });
}
function reconcileCoarse(g={}){const rows=coarseRows(g),total=rows.reduce((n,r)=>n+r.n_months,0),monthly=(g.monthly||[]).length;return {total,monthly,unknown:rows.find(r=>r.regime==='UNKNOWN').n_months,matches:total===monthly};}
function campaignEvidence(catalog,record){
 const campaign=(catalog.campaigns||[]).find(c=>c.campaign_id===record.campaign_id),oos=campaign?.oos;
 return {campaign_id:record.campaign_id,evidence_class:oos?.evidence_class||'NOT_RECORDED',signal_start:oos?.start||null,
  signal_end:oos?.signal_end||null,return_end:oos?.return_end||null,prior_exposure_count:Array.isArray(oos?.prior_exposure_ids)?oos.prior_exposure_ids.length:null,
  evaluated:record.validation?.confirmation_status==='EVALUATED',source_pointer:campaign?'/campaigns/'+catalog.campaigns.indexOf(campaign)+'/oos':null};
}
function diagnosticCoverage(records){
 const keys=['input_quality','controlled_comparison','economic_outcomes','execution_costs','monthly_performance','selection_profile'];
 return keys.map(section=>({section,total:records.length,status_counts:records.reduce((a,r)=>{const key=r.diagnostics?.[section]?.status||'NOT_RECORDED';a[key]=(a[key]||0)+1;return a;},{})}));
}
function previousCompletedMonth(asOf){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(asOf))throw Error('Explicit KST display audit date required');
 const [y,m,d]=asOf.split('-').map(Number),date=new Date(Date.UTC(y,m-1,d));
 if(date.toISOString().slice(0,10)!==asOf)throw Error('Invalid display audit date');
 return new Date(Date.UTC(y,m-2,1)).toISOString().slice(0,7);
}
const ordinal=s=>{if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(s||''))return null;const [y,m]=s.split('-').map(Number);return y*12+m;};
function displayFreshness(snapshot,asOf){
 const expected=previousCompletedMonth(asOf),end=ordinal(expected);
 const contexts=(snapshot?.contexts||[]).map(c=>{
  const source=ordinal(c.data_latest_month),usable=ordinal(c.latest_usable_month),lag=source===null?null:end-source,usableLag=usable===null?null:end-usable;
  // A historical READY flag is not rerun for a new month. Do not carry a state forward here.
  const ready=usable===end&&source!==null&&source>=end&&c.latest_status==='READY';
  return {...c,display_freshness:{expected_completed_month:expected,source_lag_months:lag,latest_usable_lag_months:usableLag,
   current_state_ready:ready,status:ready?'COVERED_IN_PRESERVED_SNAPSHOT':'CURRENT_MONTH_NOT_ESTABLISHED'}};
 });
 return {display_audit_as_of:asOf,source_snapshot_as_of:snapshot?.as_of||null,expected_completed_month:expected,
  preserved_ready_contexts:snapshot?.current_ready_contexts??null,current_ready_contexts:contexts.filter(c=>c.display_freshness.current_state_ready).length,
  context_count:contexts.length,contexts,source_refreshed:false,factor_evaluation_executed:false};
}
const CONTEXT_NAMES={KRX_KOSPI_MONTH_END_ASSUMED:'KOSPI · 월말 시장 국면',KR_PRODUCTION_INFLATION_DIRECTION:'한국 생산·물가 · 방향 조합',KR_POLICY_DIRECTION_3M:'한국 기준금리 · 3개월 방향',
 KR_CPI_YOY:'한국 소비자물가 · 전년비',KR_CPI_MOM:'한국 소비자물가 · 전월비',KR_PPI_YOY:'한국 생산자물가 · 전년비',KR_PPI_MOM:'한국 생산자물가 · 전월비',
 KR_INDUSTRIAL_PRODUCTION_YOY:'한국 산업생산 · 전년비',KR_INDUSTRIAL_PRODUCTION_MOM:'한국 산업생산 · 전월비',KR_RETAIL_SALES_MOM:'한국 소매판매 · 전월비',
 KR_TRADE_BALANCE:'한국 무역수지',KR_CURRENT_ACCOUNT:'한국 경상수지',KR_UNEMPLOYMENT_RATE:'한국 실업률',KR_BUSINESS_CONFIDENCE:'한국 기업신뢰',KR_CONSUMER_CONFIDENCE:'한국 소비자신뢰',CN_NBS_MANUFACTURING_PMI:'중국 제조업 구매관리자지수',
 AUDUSD:'호주달러 / 미국달러',EURUSD:'유로 / 미국달러',USDCNH:'미국달러 / 역외 위안',USDCNY:'미국달러 / 위안',USDJPY:'미국달러 / 엔',USDTWD:'미국달러 / 대만달러',
 EEM:'신흥국 주식 · EEM',EWT:'대만 주식 · EWT',EWY:'한국 주식 · EWY',FXI:'중국 대형주 · FXI',VIX3M:'3개월 변동성 지수',VIX9D:'9일 변동성 지수',VVIX:'VIX의 변동성 지수',
 CL:'원유 · COT 포지션',DX:'달러지수 · COT 포지션',GC:'금 · COT 포지션',HG:'구리 · COT 포지션',J6:'일본 엔 · COT 포지션',VX:'변동성 선물 · COT 포지션',ZB:'미국 장기국채 · COT 포지션',ZN:'미국 10년 국채 · COT 포지션',ZQ:'미국 정책금리 선물 · COT 포지션',ZT:'미국 2년 국채 · COT 포지션'};
function contextLabel(id){return CONTEXT_NAMES[id]||CONTEXT_NAMES[String(id).replace('FMP_ASSUMED_','')]||String(id);}
function displayCheckName(name){return name==='IC 레짐 집중도'?'시간구간별 IC 집중도':name;}
function reviewStanceLabel(stance){return {SUPPORTS:'교훈과 부합',UNCERTAIN:'교훈 판단 유보',CONTRADICTS:'교훈과 충돌'}[stance]||stance;}

// Display policy only. Preserve frozen verdicts, gate results, packets and Gold status.
// A sealed or incomplete PROVISIONAL is NOT a failure. Only the completed legacy
// neutralization failures are folded into the rejected display bucket.
function researchVerdict(record){
 const v=record?.validation||{},historical=v.verdict||'NOT_RECORDED';
 const legacyFailure=historical==='PROVISIONAL'&&v.confirmation_status==='EVALUATED'&&
  (v.failed_checks||[]).some(c=>c.tier==='T3.2'&&c.passed===false);
 const code=historical==='REJECT'||legacyFailure?'REJECT':historical==='PROMOTE'?'PROMOTE':'PENDING';
 return {code,label:{PROMOTE:'승격 통과',REJECT:'승격 탈락',PENDING:'검증 중'}[code],
  historical_verdict:historical,reclassified:legacyFailure,
  reason:legacyFailure?'고유 예측력 기준 미충족':code==='PENDING'?'최종 승격 판단 미완료':null};
}
function researchVerdictCounts(records){
 return records.reduce((counts,r)=>{counts[researchVerdict(r).code]++;return counts;},{PROMOTE:0,REJECT:0,PENDING:0});
}

window.ResearchSemantics=Object.freeze({COARSE_STATES,cycleOf,campaignDay,chronological,selectStudies,coarseRows,reconcileCoarse,campaignEvidence,diagnosticCoverage,previousCompletedMonth,displayFreshness,contextLabel,displayCheckName,reviewStanceLabel,researchVerdict,researchVerdictCounts,displayAuditAsOf:"2026-10-01"});
})();
