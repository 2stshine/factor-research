import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {coarseRows,reconcileCoarse,selectStudies,displayFreshness,campaignEvidence,diagnosticCoverage,contextLabel,displayCheckName,reviewStanceLabel} from '../src/research-status/semantics.mjs';
import {researchVerdict,researchVerdictCounts} from '../src/research-status/semantics.mjs';
const catalog=JSON.parse(await readFile(new URL('../dist/data/research-catalog.json',import.meta.url),'utf8'));
const frozen=JSON.stringify(catalog);
const known=Array.from({length:12},(_,i)=>({month:`k${i}`,regime:'UP_LOW'}));
const unknown=Array.from({length:6},(_,i)=>({month:`u${i}`,regime:'UNKNOWN'}));
const fixture={monthly:[...known,...unknown],regimes:[{regime:'UP_LOW',n_months:12,rank_ic:{mean:.1,ci95:[0,.2]}}]};
assert.deepEqual(reconcileCoarse(fixture),{total:18,monthly:18,unknown:6,matches:true});
const u=coarseRows(fixture).find(r=>r.regime==='UNKNOWN');assert.equal(u.n_months,6);assert.equal(u.rank_ic.mean,null);assert.equal(u.n_joint_usable_episodes,null);
assert.equal(coarseRows(fixture).find(r=>r.regime==='DOWN_LOW').n_months,0);
assert.throws(()=>coarseRows({...fixture,regimes:[{regime:'UP_LOW',n_months:11}]}),/mismatch/);
assert.throws(()=>coarseRows({monthly:[{regime:'UNRECOGNIZED'}]}),/Unrecognized/);
const old={record_id:'old',campaign_id:'campaign-20260901-001',provenance:{cycle:'cycle-0200-old'},regimes:fixture};
const fresh={record_id:'new',campaign_id:'campaign-20260902-001',provenance:{cycle:'cycle-0201-new'},regimes:{}};
assert.equal(selectStudies({records:[]}).latestResearch,null);assert.equal(selectStudies({records:[fresh]}).selectedRegimeStudy,null);
assert.equal(selectStudies({records:[old,fresh]}).latestResearch.record_id,'new');assert.equal(selectStudies({records:[old,fresh]}).selectedRegimeStudy.record_id,'old');
assert.equal(selectStudies({records:[old,{...fresh,regimes:fixture}]}).regimeStudies.length,2);
const current=displayFreshness(catalog.regime_input_snapshot,'2026-10-01');assert.equal(current.expected_completed_month,'2026-09');assert.equal(current.current_ready_contexts,0);assert.equal(current.preserved_ready_contexts,38);assert.equal(current.context_count,39);
assert.equal(displayFreshness(catalog.regime_input_snapshot,'2026-09-23').current_ready_contexts,38);
assert.equal(displayFreshness({contexts:[]},'2026-01-01').expected_completed_month,'2025-12');
assert.throws(()=>displayFreshness({},'2026-02-31'),/Invalid/);
const selected=selectStudies(catalog);assert.equal(selected.latestResearch.factor_name,'return_trading_activity_correlation_12m');assert.equal(selected.regimeStudies.length,1);
assert.deepEqual(reconcileCoarse(selected.selectedRegimeStudy.regimes),{total:63,monthly:63,unknown:0,matches:true});
assert.equal(campaignEvidence(catalog,selected.latestResearch).prior_exposure_count,22);
assert.equal(catalog.records.filter(r=>campaignEvidence(catalog,r).evaluated).length,36);
assert.equal(diagnosticCoverage(catalog.records).find(x=>x.section==='execution_costs').status_counts.NOT_COLLECTED,177);
assert.equal(reviewStanceLabel('SUPPORTS'),'교훈과 부합');assert.equal(displayCheckName('IC 레짐 집중도'),'시간구간별 IC 집중도');
assert.equal(contextLabel('FMP_ASSUMED_KR_INDUSTRIAL_PRODUCTION_YOY'),'한국 산업생산 · 전년비');
assert.equal(JSON.stringify(catalog),frozen);
assert.deepEqual(researchVerdictCounts(catalog.records),{PROMOTE:29,REJECT:148,PENDING:0});
assert.equal(catalog.counts.verdicts.REJECT,142,'Stored historical counts must not change');
const provisional=catalog.records.filter(r=>r.validation.verdict==='PROVISIONAL');
assert.equal(provisional.length,6);
for(const r of provisional){
 const v=researchVerdict(r);
 assert.equal(v.code,'REJECT');assert.equal(v.reason,'고유 예측력 기준 미충족');
 assert.equal(v.historical_verdict,'PROVISIONAL');assert.equal(v.reclassified,true);
}
for(const validation of [
 {verdict:'PROVISIONAL',confirmation_status:'SEALED',failed_checks:[{tier:'T3.2',passed:false}]},
 {verdict:'PROVISIONAL',confirmation_status:'EVALUATED',failed_checks:[]},
 {verdict:'PROVISIONAL',confirmation_status:'EVALUATED',failed_checks:[{tier:'T3.2',passed:null}]},
 {verdict:'PROVISIONAL',confirmation_status:'EVALUATED',failed_checks:[{tier:'T3.1',passed:false}]},
 {}
])assert.equal(researchVerdict({validation}).code,'PENDING','Do not blanket-reject incomplete/unsupported PROVISIONAL');
assert.equal(researchVerdict({validation:{verdict:'PROMOTE'}}).label,'승격 통과');
assert.equal(JSON.stringify(catalog),frozen,'Display policy must preserve original records');
console.log('PASS: 29 passed / 148 rejected / 0 pending; all 6 legacy completed failures grouped; sealed, pending, unknown and unrelated soft failures not relabeled; original evidence unchanged.');
console.log('PASS: UNKNOWN reconciliation; zero/one/two regime studies; independent latest research; KST freshness rollover; provenance and unchanged catalog.');
