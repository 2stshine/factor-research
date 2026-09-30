import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=path=>readFile(resolve(root,path),'utf8');
const research=JSON.parse(await read('dist/data/research-catalog.json'));
const gold=JSON.parse(await read('dist/data/gold-catalog.json'));
const code=await read('dist/app.js');
const index=await read('dist/index.html');
for(const asset of ['term-help.js','term-help.css']){
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
const context=vm.createContext({document:{querySelector:node,querySelectorAll:()=>[],addEventListener(){}},location:{hash:''},window:{addEventListener(){},scrollTo(){}},fetch:()=>new Promise(()=>{}),fixtureResearch:research,fixtureGold:gold,console,URL,Blob,setTimeout});
vm.runInContext(code,context);
vm.runInContext('research=fixtureResearch;gold=fixtureGold;latest=[...research.records].reverse().find(r=>r.regimes?.monthly?.length);',context);
const htmlCheck=html=>{assert(html.length>100);assert(!html.includes('[object Object]'),'Unformatted object in UI');assert(!/>\s*(?:NaN|undefined)\s*<|="[^"<>]*(?:NaN|undefined)[^"<>]*"/.test(html),'Invalid rendered value');};
for(const route of ['overview','factors','lessons','regimes','studies','method'])htmlCheck(vm.runInContext(`${route}()`,context));
assert.equal(vm.runInContext('ui.axis',context),'regime');
htmlCheck(vm.runInContext('regimePage()',context));
assert(vm.runInContext('regimePage()',context).includes('16조합은 작은 표본'));
vm.runInContext("ui.lessonQuery='no-such-factor'",context);
assert(vm.runInContext('lessonResults()',context).includes('0개 교훈'));
vm.runInContext("ui.lessonQuery=''",context);
if(research.regime_input_snapshot){
 assert(research.regime_input_snapshot.contexts.every(c=>c.freshness));
 assert(vm.runInContext('inputReadiness()',context).includes('최신 판독과 과거 연구는 별개'));
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
vm.runInContext("ui.query='';ui.verdict='REJECT';",context);assert.equal(vm.runInContext('filteredStudies().length',context),142);
vm.runInContext("ui.verdict='ALL';ui.review='REVIEWED';",context);assert.equal(vm.runInContext('filteredStudies().length',context),research.counts.reviewed_records);
const overview=vm.runInContext('overview()',context);assert(overview.includes('-0.65'));assert(overview.includes('0.0682'));assert(overview.includes('현재 상태 미검증')||gold.is_live);
for(const name of await readdir(resolve(root,'dist/data'))){const text=await read(`dist/data/${name}`);assert(!/postgres(?:ql)?:\/\/|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|\b(?:access_token|secret_access_key|password)\s*["']?\s*:/i.test(text),'Sensitive data');}
console.log(`PASS: 6 routes, ${research.records.length} research details, ${gold.factors.length} Gold details, ${axes.length*2} regime views; release counts, units, missing states, filters and secrets checks.`);
