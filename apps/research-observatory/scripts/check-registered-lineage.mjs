import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {project,digest} from '../src/research-map/projection.mjs';
import {registeredEdges} from '../src/research-map/registered-lineage.mjs';
const text=await readFile(new URL('../dist/data/research-catalog.json',import.meta.url),'utf8'),catalog=JSON.parse(text);
const themes=JSON.parse(await readFile(new URL('../src/research-map/themes.json',import.meta.url),'utf8'));
const original=JSON.parse(await readFile(new URL('../dist/data/research-map.json',import.meta.url),'utf8'));
const opts={catalogHash:digest(text),revision:original.revision};
assert.deepEqual(project(catalog,themes,opts),original);
const originalRecords=structuredClone(catalog.records);
const target=catalog.records.find(r=>r.provenance.cycle.startsWith('cycle-0230-'));
const source=catalog.records.find(r=>r.provenance.cycle.startsWith('cycle-0229-'));
const fixture=()=>{const c=structuredClone(catalog),r=c.records.find(r=>r.record_id===target.record_id);
 r.registered_lineage={schema_version:'registered-lineage-public-v1',status:'RECORDED_AT_REGISTRATION',reference_authentication:'CURRENT_PUBLIC_REVIEW_VERSION_AND_PACKET',
 definition_hash:r.provenance.definition_hash,strategy_sha256:r.definition.research_spec.strategy_sha256,
 declaration_hash:'d'.repeat(64),capture_id:'a'.repeat(64),knowledge_snapshot_hash:'c'.repeat(64),
 registered_at:'2030-01-01T00:02:00Z',declared_at:'2030-01-01T00:01:00Z',snapshot_captured_at:'2030-01-01T00:00:00Z',
 historical_backfill:false,follow_up_executed:false,independent_evidence:false,
 lesson_references:[{record_id:source.record_id,packet_sha256:source.provenance.packet_sha256,review_hash:'b'.repeat(64),relation:'DECLARED_QUALITATIVE_LESSON_USE'}]};
 return {c,r,l:r.registered_lineage};};
let f=fixture(),g=project(f.c,themes,opts),edges=g.network.edges.filter(e=>e.type==='lesson_use');
assert.equal(edges.length,1);assert(edges[0].registration);assert.equal(edges[0].sources.length,3);
assert.equal(g.network.nodes.length,531);assert.equal(g.network.counts.followups_executed,0);
assert(edges[0].sources.some(s=>s.pointer.endsWith('/registered_lineage/lesson_references/0')));
// A declaration without text mention creates one lesson->hypothesis edge, never question->experiment.
f=fixture();f.r.definition.data_notes='Synthetic fixture without old lesson-key mention';g=project(f.c,themes,opts);
edges=g.network.edges.filter(e=>e.type==='lesson_use');assert.equal(edges.length,1);
assert(edges[0].from.endsWith(':lesson')&&edges[0].to.endsWith(':hypothesis'));assert.equal(edges[0].quote,undefined);
// Comparison remains comparison even when metadata is preregistered.
f=fixture();f.l.lesson_references[0].relation='DECLARED_COMPARISON_REFERENCE';g=project(f.c,themes,opts);
const comparison=g.network.edges.find(e=>e.registration);assert.equal(comparison.type,'declared_reference');assert.equal(g.network.counts.lesson_use,1);
assert(comparison.from.endsWith(':hypothesis')&&comparison.to.endsWith(':hypothesis'));
for(const change of ['withheld','schema','authentication','definition','strategy','execution','identity','packet','support','duplicate','raw_only','source_omitted','target_omitted']){
 f=fixture();let records=original.records;
 if(change==='withheld')f.l.status='WITHHELD';
 if(change==='schema')f.l.schema_version='untrusted';
 if(change==='authentication')delete f.l.reference_authentication;
 if(change==='definition')f.l.definition_hash='unknown';
 if(change==='strategy')f.l.strategy_sha256='e'.repeat(64);
 if(change==='execution')f.l.follow_up_executed=true;
 if(change==='identity')f.l.capture_id='../private-file';
 if(change==='packet')f.l.lesson_references[0].packet_sha256='f'.repeat(64);
 if(change==='support')f.l.lesson_references[0].relation='SUPPORTS';
 if(change==='duplicate')f.l.lesson_references.push(structuredClone(f.l.lesson_references[0]));
 if(change==='raw_only'){delete f.r.registered_lineage;f.r.definition.research_spec.knowledge_lineage=f.l;}
 if(change==='source_omitted')records=records.filter(r=>r.id!==source.record_id);
 if(change==='target_omitted')records=records.filter(r=>r.id!==target.record_id);
 assert.equal(registeredEdges(f.c,records).length,change==='duplicate'?1:0,change);
}
assert.deepEqual(catalog.records,originalRecords);
console.log('PASS: legacy graph unchanged; future registration/use/comparison, duplicate merge, 13 negative boundaries, no raw-declaration authority or executed follow-up. Synthetic future metadata only.');
