import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=path=>readFile(resolve(root,path),'utf8');
const research=JSON.parse(await read('dist/data/research-catalog.json'));
const gold=JSON.parse(await read('dist/data/gold-catalog.json'));
const comparison=JSON.parse(await read('dist/data/monthly-comparison.json'));
const code=await read('dist/app.js');
const index=await read('dist/index.html');
for(const asset of ['term-help.js','term-help.css','research-map.js','research-map.css','research-semantics.js','research-status.js','research-status.css','monthly-readiness.js']){
 assert(index.includes(`./${asset}`),`Missing term-help asset reference: ${asset}`);
 const content=await read(`dist/${asset}`);
 assert(content.length>0,`Empty term-help asset: ${asset}`);
 if(asset.endsWith('.js'))new vm.Script(content,{filename:asset});
}
assert.equal(research.records.length,research.counts.released_records);
assert.equal(research.counts.ledger_records,research.counts.released_records+research.counts.withheld_records);
assert.equal(gold.factors.length,gold.approved_count);
assert.equal(new Set(gold.factors.map(f=>f.name)).size,gold.factors.length);
assert(research.records.every(r=>r.provenance.packet_sha256&&r.visibility!=='PENDING'));
assert.equal(research.records.filter(r=>r.review_status==='REVIEWED_CURRENT').length,research.counts.reviewed_records);
assert.equal(research.records.filter(r=>r.validation.verdict==='PROMOTE').length,research.counts.verdicts.PROMOTE);
const nodes=new Map();
const node=selector=>{if(!nodes.has(selector))nodes.set(selector,{innerHTML:'',textContent:'',open:false,scrollTop:0,addEventListener(){},showModal(){this.open=true;},close(){this.open=false;},scrollIntoView(){}});return nodes.get(selector);};
const context=vm.createContext({document:{querySelector:node,querySelectorAll:()=>[],addEventListener(){}},location:{hash:''},window:{addEventListener(){},scrollTo(){}},fetch:()=>new Promise(()=>{}),fixtureResearch:research,fixtureGold:gold,fixtureComparison:comparison,console,URL,URLSearchParams,Blob,setTimeout,structuredClone});
vm.runInContext(await read('dist/research-semantics.js'),context);
vm.runInContext(await read('dist/monthly-readiness.js'),context);
vm.runInContext(await read('dist/comparison.js'),context);
vm.runInContext(await read('dist/research-status.js'),context);
vm.runInContext(code,context);
vm.runInContext('research=fixtureResearch;gold=fixtureGold;comparison=fixtureComparison;({latestResearch,selectedRegimeStudy}=window.ResearchSemantics.selectStudies(research));',context);
const htmlCheck=html=>{assert(html.length>100);assert(!html.includes('[object Object]'),'Unformatted object in UI');assert(!/>\s*(?:NaN|undefined)\s*<|="[^"<>]*(?:NaN|undefined)[^"<>]*"/.test(html),'Invalid rendered value');};
for(const route of ['overview','factors','lessons','regimes','studies','method','researchMap'])htmlCheck(vm.runInContext(`${route}()`,context));
htmlCheck(vm.runInContext('comparisonPage()',context));
assert(vm.runInContext('coveragePage()',context).includes('팩터 공간'));
assert(index.includes('href="#comparison"')&&index.includes('./comparison.js'));
assert.equal(comparison.factor_count,49);
assert.equal(comparison.factors.length,49);
assert.equal(new Set(comparison.factors.map(f=>f.name)).size,49);
assert.equal(comparison.completed_comparisons,0);
assert.equal(comparison.planned_comparisons,196);
assert.equal(comparison.real_performance_computed,false);
assert.equal(comparison.independent_oos,false);
assert.equal(comparison.historical_definition_changed,36);
assert.equal(comparison.historical_definition_unknown,13);
assert(comparison.factors.every(f=>f.status==='APPROVED'&&f.frequency==='daily'&&f.comparison_status==='NOT_COMPUTED'&&!f.performance));
assert(vm.runInContext('comparisonPage()',context).includes('실제 성과는 아직 미산출'));
assert(vm.runInContext('freshness()',context).includes('DB 재확인'));
assert(!vm.runInContext('freshness()',context).includes('로그인 만료'));
assert(vm.runInContext("comparisonFactors('no-such-factor')",context).includes('검색 결과가 없습니다'));
assert(vm.runInContext("comparisonFactors('중기 모멘텀')",context).includes('1개 현재 승인 버전'));
vm.runInContext('comparison=null',context);
assert(vm.runInContext('comparisonPage()',context).includes('불러오지 못했습니다'));
vm.runInContext('comparison=fixtureComparison',context);
const originalStudies=vm.runInContext('({research,latestResearch,selectedRegimeStudy})',context);
context.originalStudies=originalStudies;
vm.runInContext('research={...fixtureResearch,records:fixtureResearch.records.map(r=>({...r,regimes:{}}))};selectedRegimeStudy=null',context);
assert(vm.runInContext('methodInputStatus()',context).includes('공개된 레짐 연구가 없어'));
vm.runInContext('research=structuredClone(fixtureResearch);({latestResearch,selectedRegimeStudy}=window.ResearchSemantics.selectStudies(research));getRegimeStudy().regimes.input_status={verified_context_ids:["A","B"],assumed_context_ids:["X","Y","Z"]}',context);
assert(vm.runInContext('methodInputStatus()',context).includes('검증 분류 입력 2축'));
assert(vm.runInContext('methodInputStatus()',context).includes('가정 입력 3축'));
vm.runInContext('({research,latestResearch,selectedRegimeStudy}=originalStudies)',context);
assert.equal(vm.runInContext('ui.axis',context),'regime');
htmlCheck(vm.runInContext('regimePage()',context));
assert(vm.runInContext('regimePage()',context).includes('작은 표본'));
vm.runInContext("ui.lessonQuery='no-such-factor'",context);
assert(vm.runInContext('lessonResults()',context).includes('0개 교훈'));
vm.runInContext("ui.lessonQuery=''",context);
const originalLessonIds=research.records.map(r=>r.record_id);
const lessonIds=expression=>JSON.parse(vm.runInContext(`JSON.stringify(${expression}.map(r=>r.record_id))`,context));
const orderedLessons=lessonIds('sortedLessons()');
assert.deepEqual(orderedLessons.slice(0,2),[
 'campaign-20260921-001/epoch-001/return_trading_activity_correlation_12m',
 'campaign-20260920-001/epoch-001/operating_asset_growth_12m'
]);
assert.deepEqual(lessonIds('sortedLessons([...research.records].reverse())'),orderedLessons,'Order depends on export array');
const lessonFixture=(id,campaign,cycle)=>({record_id:id,campaign_id:campaign,provenance:{cycle},review_status:'REVIEWED_CURRENT'});
context.lessonFixtures=[
 lessonFixture('old','campaign-20260920-001','cycle-9999-old'),
 lessonFixture('same-day-9','campaign-20260921-002','cycle-9-a'),
 lessonFixture('same-day-10','campaign-20260921-001','cycle-10-b'),
 lessonFixture('missing',undefined,'cycle-9999-missing'),
 lessonFixture('invalid','campaign-20260230-001','cycle-9998-invalid'),
 {...lessonFixture('unreviewed','campaign-20260930-001','cycle-99999'),review_status:'UNREVIEWED'}
];
assert.deepEqual(lessonIds('sortedLessons(lessonFixtures)'),['same-day-10','same-day-9','old','missing','invalid']);
assert.deepEqual(lessonIds('sortedLessons([...lessonFixtures].reverse())'),lessonIds('sortedLessons(lessonFixtures)'));
assert.equal(vm.runInContext("lessonSequence({provenance:{cycle:'not-a-cycle'}})",context),null);
assert(vm.runInContext('lessonChronology(lessonFixtures[3])',context).includes('날짜 미확인'));
const idsInCards=html=>[...html.matchAll(/data-record="([^"]+)"/g)].map(m=>m[1]);
assert.deepEqual(idsInCards(vm.runInContext('lessonResults()',context)),orderedLessons);
assert.deepEqual(idsInCards(vm.runInContext('overview()',context)).slice(-4),orderedLessons.slice(0,4));
vm.runInContext("ui.lessonQuery='campaign-20260814'",context);
assert.deepEqual(idsInCards(vm.runInContext('lessonResults()',context)),orderedLessons.filter(id=>id.startsWith('campaign-20260814')));
vm.runInContext("ui.lessonQuery=''",context);
assert.deepEqual(research.records.map(r=>r.record_id),originalLessonIds,'Lesson sorting mutated snapshot');
for(const record of research.records.filter(r=>r.review_status==='REVIEWED_CURRENT')){
 context.localizedRecord=record;
 const heading=vm.runInContext('lessonTitle(localizedRecord)',context);
 assert(/[가-힣]/.test(heading)&&heading.length<=100,`Missing/readability issue in Korean lesson title: ${record.record_id}`);
 assert(!heading.includes(record.review.lesson_key),'Internal lesson key used as title');
 assert(!/[A-Za-z_]/.test(vm.runInContext('title(localizedRecord.factor_name)',context)),`Untranslated factor: ${record.factor_name}`);
 assert.notEqual(vm.runInContext('reviewLabel(localizedRecord.review.stance)',context),'판정 미확인');
 const card=vm.runInContext('lessonCard(localizedRecord)',context);
 assert(card.includes('원본 연구 식별자')&&card.includes(record.review.lesson_key),'Original provenance lost');
}
vm.runInContext("ui.lessonQuery='아미후드 비유동성 평균'",context);
assert(vm.runInContext('lessonResults()',context).includes('4개 교훈'),'Korean factor-name search failed');
vm.runInContext("ui.lessonQuery='판단 유보'",context);
assert(!vm.runInContext('lessonResults()',context).includes('가설과 부합'),'Korean stance search failed');
vm.runInContext("ui.lessonQuery=''",context);
if(research.regime_input_snapshot){
 assert(research.regime_input_snapshot.contexts.every(c=>c.freshness));
 assert(vm.runInContext('inputReadiness()',context).includes('데이터를 새로 수집하거나 상태를 재계산한 것이 아닙니다'));
 assert.equal(research.regime_input_snapshot.current_ready_contexts,research.regime_input_snapshot.contexts.filter(c=>c.freshness.current_state_ready).length);
}
for(const r of research.records){context.recordId=r.record_id;vm.runInContext('openRecord(recordId)',context);htmlCheck(node('#detail-content').innerHTML);}
for(const f of gold.factors){context.factorName=f.name;vm.runInContext('openFactor(factorName)',context);htmlCheck(node('#detail-content').innerHTML);}
assert.equal(vm.runInContext('ui.factorSort',context),'discovery_asc');
assert.equal(gold.factors.filter(f=>f.discovery?.discovered_at).length,35);
assert(gold.factors.every(f=>f.discovery?.name===f.name));
const chronologyNames=()=>JSON.parse(vm.runInContext('JSON.stringify(filteredFactors().map(f=>f.name))',context));
const originalNames=gold.factors.map(f=>f.name);
const expected=gold.factors.filter(f=>f.discovery.discovered_at).sort((a,b)=>Date.parse(a.discovery.discovered_at)-Date.parse(b.discovery.discovered_at)||a.discovery.discovery_sequence-b.discovery.discovery_sequence||a.name.localeCompare(b.name,'en')).map(f=>f.name);
const unknown=gold.factors.filter(f=>!f.discovery.discovered_at).map(f=>f.name).sort((a,b)=>a.localeCompare(b,'en'));
assert.deepEqual(chronologyNames(),[...expected,...unknown]);
assert.equal(chronologyNames()[0],'trading_turnover_20d');
vm.runInContext("ui.factorSort='discovery_desc'",context);
assert.deepEqual(chronologyNames(),[...expected].reverse().concat(unknown));
vm.runInContext("ui.factorSort='name'",context);
assert.deepEqual(chronologyNames(),[...originalNames].sort((a,b)=>a.localeCompare(b,'en')));
vm.runInContext("ui.factorSort='discovery_asc';ui.factorQuery='return_kurtosis_24m'",context);
assert.equal(chronologyNames().length,1);
assert(vm.runInContext('factorResults()',context).includes('과거 정의 불일치'));
vm.runInContext("ui.factorQuery='no-such-factor'",context);
assert(vm.runInContext('factorResults()',context).includes('colspan="8"'));
vm.runInContext("ui.factorQuery='';ui.category='value'",context);
assert(vm.runInContext("filteredFactors().length>0&&filteredFactors().every(f=>f.category==='value')",context));
vm.runInContext("ui.category='ALL'",context);
assert.deepEqual(gold.factors.map(f=>f.name),originalNames,'Sorting mutated snapshot');
for(const f of gold.factors.filter(f=>f.discovery.discovered_at)){
 assert.equal(f.discovery.definition_hash,f.definition_hash);
 assert.equal(f.discovery.definition_binding,'CATALOG_AND_RESEARCH_DEFINITION_HASH_MATCH');
 assert(f.discovery.source_refs.length>0);
}
const regime=research.records.find(r=>r.regimes?.monthly?.length).regimes;
const axes=['trend_long','trend_short','volatility_long','volatility_short','regime','regime_detail','trend_phase','volatility_phase',...Object.keys(regime.macro_views)];
for(const axis of axes){for(const metric of ['rank_ic','top_minus_bottom']){context.axis=axis;context.metric=metric;htmlCheck(vm.runInContext('ui.axis=axis;ui.metric=metric;regimeResults()',context));}}
assert.equal(regime.monthly.length,63);
assert.equal(Object.keys(regime.macro_views).length,37);
assert.equal(regime.views.regime_detail.length,17);
assert.equal(Object.values(regime.macro_views).reduce((n,v)=>n+v.states.length,0),112);
for(const view of [regime.regimes,...Object.values(regime.views),...Object.values(regime.macro_views).map(v=>v.states)])assert.equal(view.reduce((n,r)=>n+r.n_months,0),63);
vm.runInContext("ui.query='no-such-factor';",context);htmlCheck(vm.runInContext('studyResults()',context));
assert(vm.runInContext('studyResults()',context).includes('0개 연구 기록'));
vm.runInContext("ui.query='';ui.verdict='REJECT';",context);assert.equal(vm.runInContext('filteredStudies().length',context),148);
assert(vm.runInContext('outcomes()',context).includes('승격 탈락 <strong>148</strong>'));
assert(!vm.runInContext('studies()',context).includes('value="PROVISIONAL"'));
vm.runInContext("ui.verdict='PENDING'",context);assert.equal(vm.runInContext('filteredStudies().length',context),0);
for(const record of research.records.filter(r=>r.validation.verdict==='PROVISIONAL')){
 context.provisionalRecord=record;
 assert(vm.runInContext('researchVerdictBadge(provisionalRecord)',context).includes('승격 탈락'));
 vm.runInContext('openRecord(provisionalRecord.record_id)',context);
 assert(node('#detail-content').innerHTML.includes('고유 예측력 기준 미충족'));
 assert(node('#detail-content').innerHTML.includes('당시 판정: <code>PROVISIONAL</code>'));
}
vm.runInContext("ui.verdict='ALL';ui.review='REVIEWED';",context);assert.equal(vm.runInContext('filteredStudies().length',context),research.counts.reviewed_records);
assert(!vm.runInContext('overview()+lessons()+lessonResults()',context).includes('가설과 부합'));
assert(vm.runInContext('inputReadiness()',context).includes('0/39'));
assert(vm.runInContext('inputReadiness()',context).includes('한국 산업생산 · 전년비'));
assert.equal(vm.runInContext('coarseRows(getRegimeStudy().regimes).length',context),5);
const overview=vm.runInContext('overview()',context);assert(overview.includes('-0.65'));assert(overview.includes('0.0682'));assert(overview.includes('성과는 과거 정의와 구분'));
for(const name of await readdir(resolve(root,'dist/data'))){const text=await read(`dist/data/${name}`);assert(!/postgres(?:ql)?:\/\/|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|\b(?:access_token|secret_access_key|password)\s*["']?\s*:/i.test(text),'Sensitive data');}
console.log(`PASS: 9 routes, ${research.records.length} research details, ${gold.factors.length} Gold details, current 49 identities, ${axes.length*2} regime views; release counts, units, missing states, filters and secrets checks.`);
