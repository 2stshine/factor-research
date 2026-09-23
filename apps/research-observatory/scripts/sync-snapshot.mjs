import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
// Packages authenticated generated data; never reads campaign/OOS originals.
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const source=resolve(process.argv[2]||resolve(root,'../../output/research-dashboard-source'));
const chronology=JSON.parse(await readFile(resolve(source,'discovery-order.json'),'utf8'));
if(chronology.schema_version!=='gold-discovery-order-v1')throw new Error('Unsupported chronology schema');
const chronologyByName=new Map(chronology.factors.map(f=>[f.name,f]));
if(chronologyByName.size!==chronology.factors.length)throw new Error('Duplicate chronology names');
await mkdir(resolve(root,'dist/data'),{recursive:true});
for(const name of ['research-catalog','gold-catalog']){
 const text=await readFile(resolve(source,`${name}.json`),'utf8');const data=JSON.parse(text);
 if(name==='research-catalog'){
  if(data.records.length!==data.counts.released_records)throw new Error('Release count mismatch');
  if(data.records.some(r=>!r.provenance?.packet_sha256||r.visibility==='PENDING'))throw new Error('Unverified research row');
 }
 if(name==='gold-catalog'){
  if(data.factors.length!==chronologyByName.size)throw new Error('Chronology catalog membership mismatch');
  for(const factor of data.factors){
   const entry=chronologyByName.get(factor.name);
   if(!entry)throw new Error(`Missing chronology: ${factor.name}`);
   if(entry.discovered_at&&(!Number.isFinite(Date.parse(entry.discovered_at))||entry.definition_hash!==factor.definition_hash||entry.definition_binding!=='CATALOG_AND_RESEARCH_DEFINITION_HASH_MATCH'||!entry.source_refs?.length))throw new Error(`Unbound chronology: ${factor.name}`);
   factor.discovery=entry;
  }
  const {factors,...metadata}=chronology;
  data.discovery_order=metadata;
 }
 if(/postgres(?:ql)?:\/\/|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|\b(?:access_token|secret_access_key|password)\s*["']?\s*:/i.test(JSON.stringify(data)))throw new Error('Unexpected sensitive field');
 await writeFile(resolve(root,'dist/data',`${name}.json`),JSON.stringify(data));
 console.log(`${name}: ${name==='research-catalog'?data.records.length:data.factors.length} rows`);
}
