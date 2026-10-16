// A standard-library AST parser reads only frozen definition fields over stdin.
// It does not import snippets, read data sources, evaluate candidates or use outcomes.
import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const hash=s=>createHash('sha256').update(s).digest('hex');
const stable=v=>Array.isArray(v)?v.map(stable):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,stable(v[k])])):v;
export function validateSourceStructure(value,catalog,catalogHash){
 if(value.schema_version!=='frozen-source-structure-v1'||value.scope!=='AUTHENTICATED_RELEASED_RECORDS_ONLY'||value.catalog_sha256!==catalogHash||value.records.length!==catalog.records.length||value.performance_used!==false||value.independent_dimension_computed!==false)throw Error('Source diagnostic scope mismatch');
 const originals=new Map(catalog.records.map(r=>[r.record_id,r]));
 if(new Set(value.records.map(r=>r.record_id)).size!==originals.size)throw Error('Duplicate source diagnostic identity');
 for(const row of value.records){const r=originals.get(row.record_id);
  if(!r||row.definition_hash!==r.provenance.definition_hash||row.packet_sha256!==r.provenance.packet_sha256||row.source_sha256!==hash(r.definition.source)||row.params_sha256!==hash(JSON.stringify(stable(r.definition.params))))throw Error('Frozen source diagnostic binding mismatch');
  if(row.analysis.runtime_or_pit_verified!==false||row.analysis.calendar_continuity_verified!==false||row.analysis.economic_mechanism!=='NOT_INFERRED')throw Error('Source analysis overclaims verification');
 }
 return value;
}
export function buildSourceStructure(root,catalog,catalogHash){
 if(catalog.records.some(r=>r.visibility!=='RELEASED_QUALITATIVE'||r.provenance?.authentication!=='CURRENT_RELEASE_STATE_AND_EXACT_PACKET_REBUILD'))throw Error('Unreleased source diagnostic input');
 const payload={scope:'AUTHENTICATED_RELEASED_RECORDS_ONLY',catalog_sha256:catalogHash,records:catalog.records.map(r=>({record_id:r.record_id,definition_hash:r.provenance.definition_hash,packet_sha256:r.provenance.packet_sha256,source:r.definition.source,params:r.definition.params}))};
 const result=spawnSync(process.env.OBSERVATORY_PYTHON||'python3',['-B',resolve(root,'src/research-status/source_structure.py')],{input:JSON.stringify(payload),encoding:'utf8',maxBuffer:8*1024*1024,timeout:15000});
 if(result.error||result.status!==0)throw Error('Frozen source AST diagnostic failed: '+(result.error?.message||result.stderr.trim()));
 return validateSourceStructure(JSON.parse(result.stdout),catalog,catalogHash);
}
