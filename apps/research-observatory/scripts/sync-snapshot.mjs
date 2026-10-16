import {buildResearchMap} from './build-research-map.mjs';
import {buildMonthlyReadiness} from './build-monthly-readiness.mjs';
import {buildResearchStatus} from './build-research-status.mjs';
import {readFile,writeFile,mkdir,mkdtemp,cp,rm,rename,unlink} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {randomUUID,createHash} from 'node:crypto';
const here=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export const generatedAssets=Object.freeze(['data/research-catalog.json','data/gold-catalog.json',
 'data/research-map.json','research-map.js','research-map.css','data/research-status.json',
 'research-semantics.js','research-status.js','research-status.css','data/monthly-preparation.json','monthly-readiness.js']);
const hash=b=>b===null?null:createHash('sha256').update(b).digest('hex');
async function readOptional(p){try{return await readFile(p);}catch(e){if(e.code==='ENOENT')return null;throw e;}}
async function atomicWrite(path,bytes){
 await mkdir(dirname(path),{recursive:true});const temp=path+'.pending-'+randomUUID();
 try{await writeFile(temp,bytes,{flag:'wx'});await rename(temp,path);}finally{await unlink(temp).catch(e=>{if(e.code!=='ENOENT')throw e;});}
}
// Generate every derived artifact before changing any currently served file.
// The input is an already authenticated exporter bundle; no original OOS/DB reads.
export async function stageSnapshot(root,source){
 const previous=Object.fromEntries(await Promise.all(generatedAssets.map(async name=>[name,await readOptional(resolve(root,'dist',name))])));
 const temp=await mkdtemp(resolve(tmpdir(),'observatory-snapshot-'));
 try{
  await cp(resolve(root,'src'),resolve(temp,'src'),{recursive:true});
  await mkdir(resolve(temp,'dist/data'),{recursive:true});
  const comparison=await readOptional(resolve(root,'dist/data/monthly-comparison.json'));
  if(comparison)await writeFile(resolve(temp,'dist/data/monthly-comparison.json'),comparison);
  const chronology=JSON.parse(await readFile(resolve(source,'discovery-order.json'),'utf8'));
  if(chronology.schema_version!=='gold-discovery-order-v1')throw Error('Unsupported chronology schema');
  const chronologyByName=new Map(chronology.factors.map(f=>[f.name,f]));
  if(chronologyByName.size!==chronology.factors.length)throw Error('Duplicate chronology names');
  for(const name of ['research-catalog','gold-catalog']){
   const data=JSON.parse(await readFile(resolve(source,`${name}.json`),'utf8'));
   if(name==='research-catalog'){
    if(data.records.length!==data.counts.released_records)throw Error('Release count mismatch');
    if(data.records.some(r=>!r.provenance?.packet_sha256||r.visibility!=='RELEASED_QUALITATIVE'||r.provenance.authentication!=='CURRENT_RELEASE_STATE_AND_EXACT_PACKET_REBUILD'))throw Error('Unverified research row');
   }else{
    if(data.factors.length!==chronologyByName.size)throw Error('Chronology catalog membership mismatch');
    for(const factor of data.factors){
     const entry=chronologyByName.get(factor.name);if(!entry)throw Error(`Missing chronology: ${factor.name}`);
     if(entry.discovered_at&&(!Number.isFinite(Date.parse(entry.discovered_at))||entry.definition_hash!==factor.definition_hash||entry.definition_binding!=='CATALOG_AND_RESEARCH_DEFINITION_HASH_MATCH'||!entry.source_refs?.length))throw Error(`Unbound chronology: ${factor.name}`);
     factor.discovery=entry;
    }
    const {factors,...metadata}=chronology;data.discovery_order=metadata;
   }
   if(/postgres(?:ql)?:\/\/|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|\b(?:access_token|secret_access_key|password)\s*["']?\s*:/i.test(JSON.stringify(data)))throw Error('Unexpected sensitive field');
   await writeFile(resolve(temp,'dist/data',`${name}.json`),JSON.stringify(data));
  }
  await buildResearchMap(temp);await buildResearchStatus(temp);await buildMonthlyReadiness(temp);
  const assets=Object.fromEntries(await Promise.all(generatedAssets.map(async name=>[name,await readFile(resolve(temp,'dist',name))])));
  return {root:resolve(root),previous,assets,comparison_hash:hash(comparison)};
 }finally{await rm(temp,{recursive:true,force:true});}
}
export async function publishSnapshot(root,staged,{write=atomicWrite}={}){
 if(resolve(root)!==staged.root)throw Error('Staged output belongs to another root');
 if(generatedAssets.some(name=>!Buffer.isBuffer(staged.assets[name])||!(staged.previous[name]===null||Buffer.isBuffer(staged.previous[name]))))throw Error('Incomplete staged output');
 // Fail before writes if another task edited generated assets during staging.
 for(const name of generatedAssets)if(hash(await readOptional(resolve(root,'dist',name)))!==hash(staged.previous[name]))throw Error(`Concurrent output change: ${name}`);
 if(hash(await readOptional(resolve(root,'dist/data/monthly-comparison.json')))!==staged.comparison_hash)throw Error('Concurrent comparison input change');
 const written=[];
 try{
  for(const name of generatedAssets){
   if(hash(staged.previous[name])===hash(staged.assets[name]))continue;
   const path=resolve(root,'dist',name);
   if(hash(await readOptional(path))!==hash(staged.previous[name]))throw Error(`Concurrent output change: ${name}`);
   await write(path,staged.assets[name]);written.push(name);
  }
 }catch(error){
  const conflicts=[];
  for(const name of [...written].reverse()){
   const path=resolve(root,'dist',name);
   if(hash(await readOptional(path))!==hash(staged.assets[name])){conflicts.push(name);continue;}
   if(staged.previous[name]===null)await unlink(path);else await atomicWrite(path,staged.previous[name]);
  }
  if(conflicts.length)throw new Error(`Publish failed; concurrent edits preserved: ${conflicts.join(', ')}`,{cause:error});
  throw error;
 }
 return {files:generatedAssets.length,changed:written,sha256:Object.fromEntries(generatedAssets.map(name=>[name,hash(staged.assets[name])]))};
}
export async function syncSnapshot(root=here,source=resolve(root,'../../output/research-dashboard-source')){
 const lock=resolve(root,'.snapshot-sync.lock');await mkdir(lock); // Existing lock is never removed by a competing invocation.
 try{return await publishSnapshot(root,await stageSnapshot(root,source));}
 finally{await rm(lock,{recursive:true});}
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const result=await syncSnapshot(here,resolve(process.argv[2]||resolve(here,'../../output/research-dashboard-source')));
 console.log(`Published ${result.files} verified generated files; ${result.changed.length} changed. Original research and comparison source unchanged.`);
}
