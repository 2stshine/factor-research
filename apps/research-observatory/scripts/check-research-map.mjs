import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
import {project,digest} from '../src/research-map/projection.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>readFile(resolve(root,p),'utf8');
const raw=await read('dist/data/research-catalog.json'),catalog=JSON.parse(raw),mapping=JSON.parse(await read('src/research-map/themes.json'));
const stored=JSON.parse(await read('dist/data/research-map.json'));
const config={catalogHash:digest(raw),revision:stored.revision};
const graph=project(catalog,mapping,config);
assert.deepEqual(graph,stored,'Generated map is stale');
assert.equal(graph.counts.included,177);assert.equal(graph.counts.withheld,26);assert.equal(graph.counts.lessons,177);
assert.equal(graph.counts.independent_replications,null);
assert.equal(new Set(graph.nodes.map(n=>n.id)).size,graph.nodes.length);
const nodes=new Map(graph.nodes.map(n=>[n.id,n]));
const at=pointer=>pointer.split('/').slice(1).reduce((o,k)=>o?.[k.replaceAll('~1','/').replaceAll('~0','~')],catalog);
for(const n of graph.nodes)if(n.source?.pointer)assert.notEqual(at(n.source.pointer),undefined,`Missing node source: ${n.id}`);
for(const edge of graph.edges){
 assert(nodes.has(edge.from)&&nodes.has(edge.to),'Dangling edge');
 if(edge.source?.pointer)assert.notEqual(at(edge.source.pointer),undefined,'Missing edge source');
 if(['supports_explanation','opposes_explanation'].includes(edge.relation)){
  assert.equal(at(edge.source.pointer),edge.source.evidence_id);
  assert(edge.source.pointer.includes(edge.relation==='supports_explanation'?'/supporting_evidence/':'/opposing_evidence/'));
  assert.equal(nodes.get(edge.to).type,'explanation');
  assert.equal(nodes.get(edge.from).source.packet_sha256,edge.source.packet_sha256);
 }
 if(edge.relation==='about')assert.equal(edge.basis,'EDITORIAL_TYPED_RULE');
}
const expectedScientific=catalog.records.reduce((n,r)=>n+r.review.explanations.reduce((n,e)=>n+e.supporting_evidence.length+e.opposing_evidence.length,0),0);
assert.equal(graph.edges.filter(e=>['supports_explanation','opposes_explanation'].includes(e.relation)).length,expectedScientific,'Invented support/conflict');
assert(!graph.edges.some(e=>e.relation==='contradicts_lesson'));
assert.equal(graph.windows.filter(w=>w.phase==='discovery').reduce((n,w)=>n+w.records.length,0),177);
assert(graph.edges.some(e=>e.relation==='calendar_overlap'));
assert.equal(graph.edges.filter(e=>e.relation==='methodology_reference').length,1);
const clone=()=>JSON.parse(raw);
let fixture=clone();fixture.records[0].review_status='STALE';let g=project(fixture,mapping,config);assert.equal(g.counts.included,176);assert(!g.records.some(r=>r.id===fixture.records[0].record_id));
fixture=clone();fixture.records[0].visibility='PENDING';fixture.records[0].review.general_lesson='SEALED_DO_NOT_DISCLOSE';g=project(fixture,mapping,config);assert.equal(g.counts.included,176);assert(!JSON.stringify(g).includes('SEALED_DO_NOT_DISCLOSE'));
fixture=clone();fixture.records[0].review.packet_sha256='invalid';assert.throws(()=>project(fixture,mapping,config),/Unbound review/);
fixture=clone();fixture.records[0].review.observations[0].evidence_ids.push('unknown.evidence');assert.throws(()=>project(fixture,mapping,config),/Unknown evidence/);
fixture=clone();fixture.records.push(fixture.records[0]);assert.throws(()=>project(fixture,mapping,config),/Duplicate record/);
assert(!JSON.stringify(graph).includes('INDEPENDENT_REPLICATION'));
assert.equal(catalog.records.at(-1).diagnostics.input_quality.data.raw_input_profile.length,0,'Historical packet unexpectedly rewritten');
// Exercise every current case and node with the same source data used in the browser.
const handlers={},context=vm.createContext({window:{dispatchEvent(){},addEventListener(){}},document:{addEventListener(type,fn){handlers[type]=fn;},querySelector(){return {focus(){}};}},fetch:async()=>({ok:true,json:async()=>({...graph,network:undefined})}),Event:class Event{},console});
vm.runInContext(await read('dist/research-map.js'),context);await new Promise(r=>setTimeout(r,0));
const render=()=>context.window.ResearchMapUI.render(catalog,{title:n=>n},()=>{});
let html=render();assert(html.includes('177'));assert(html.includes('cycle-0230'));
const click=dataset=>handlers.click({target:{closest:()=>({dataset,hasAttribute:()=>false})}});
for(const r of catalog.records){
 click({rmRecord:r.record_id});
 for(const key of ['hypothesis','observations','lesson','explanations','limits','followup']){
  click({rmNode:key});html=render();assert(html.includes(r.provenance.cycle));assert(!html.includes('[object Object]'));assert(!/>\s*(?:undefined|NaN)\s*</.test(html));
 }
}
click({rmRecord:catalog.records.at(-1).record_id});click({rmNode:'explanations'});render();click({rmEvidence:'diagnostic.discovery.input_quality'});html=render();assert(html.includes('raw_input_profile'));assert(html.includes('/diagnostics/input_quality'));
for(const [key,expected] of [['observations','-0.65%p'],['followup','현재 가용성'],['limits','이 실행의 빈 raw_input_profile']]){click({rmNode:key});assert(render().includes(expected));}
handlers.input({target:{id:'rm-search',value:'NO_SUCH_STUDY'}});assert(render().includes('조건에 맞는 교훈이 없습니다'));
assert.equal((await read('src/research-map/network-view.js'))+'\n'+(await read('src/research-map/view.js')),await read('dist/research-map.js'));assert.equal(await read('src/research-map/view.css'),await read('dist/research-map.css'));
console.log(`PASS: deterministic projection; ${graph.nodes.length} IDs and ${graph.edges.length} edges; exact scientific sources; sealed/stale exclusion; binding, duplicate and unknown-evidence rejection; calendar reuse; 177 × 6 detail states; empty search; immutable old profile.`);
