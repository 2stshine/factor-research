import assert from 'node:assert/strict';
import {readFile,access} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await readFile(resolve(root,'case-0230.json'),'utf8'));
const repo=process.argv[2];
assert.equal(data.schema_version,'research-map-v1');
const ids=new Set(data.nodes.map(n=>n.id));
assert.equal(ids.size,data.nodes.length);
for(const n of data.nodes){
 assert(data.types[n.type]);assert(n.sources.length);assert(n.x>=0&&n.x+198<=1046);assert(n.y>=0&&n.y+144<=692);
 for(const s of n.sources)assert(data.sources[s],`Missing source ${s}`);
 if(n.type==='question')assert(n.proposal_origin&&/미실행|미검증/.test(n.note));
}
for(const e of data.edges){assert(ids.has(e.from)&&ids.has(e.to));assert(e.label);if(e.to.startsWith('question'))assert(e.future);}
assert.equal(data.nodes.find(n=>n.id==='cost').stat,'−0.65%');
assert.match(data.nodes.find(n=>n.id==='cost').summary,/Discovery 63개월/);
assert.match(data.nodes.find(n=>n.id==='reused').summary,/22건/);
assert.match(data.nodes.find(n=>n.id==='question_measure').summary,/아직 실행하지/);
assert.match(data.nodes.find(n=>n.id==='question_measure').callout,/입력 가용성 미확인/);
const all=JSON.stringify(data);
assert(!/postgres(?:ql)?:\/\/|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|"password"\s*:/.test(all));
for(const asset of ['index.html','map.js','map.css'])await access(resolve(root,asset));
if(repo){
 for(const s of Object.values(data.sources))await access(resolve(repo,s.path));
 const campaign=JSON.parse(await readFile(resolve(repo,'research/campaigns/campaign-20260921-001/manifest.json'),'utf8'));
 assert.equal(campaign.oos.prior_exposure_ids.length,22);assert.equal(campaign.oos.evidence_class,'HISTORICAL_REUSED_WINDOW');
 const result=JSON.parse(await readFile(resolve(repo,campaign.confirmation_result),'utf8')).confirmations[0];
 assert.equal(result.verdict,'PROMOTE');assert.equal(result.evaluation.metrics.oos_months,36);
 assert.equal(result.evaluation.metrics.net.toFixed(2),'-0.65');
 assert.equal(result.evaluation.metrics.ic_investable.toFixed(4),'0.0487');
 assert.equal(result.evaluation.metrics.oos_ic.toFixed(4),'0.0682');
 assert.equal(result.evaluation.metrics.months,63);
}
console.log(`PASS: ${data.nodes.length} nodes, ${data.edges.length} labeled edges; sources, disclosure boundaries, proposed-question status and frozen metrics.`);
