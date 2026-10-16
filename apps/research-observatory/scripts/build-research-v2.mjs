import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
if(process.argv[2]){
 const body=await readFile(resolve(process.argv[2]));const value=JSON.parse(body);
 if(value.schema_version!=='public-production-v2-v1'||value.oos_results_included!==false||value.performance_metrics_included!==false||value.production_lessons_included!==false||value.automatic_gold_publication!==false||value.legacy_campaigns_changed!==false||value.snapshot_kind!=='STATIC_PROCESS_METADATA_NOT_LIVE_RESULTS')throw Error('Not an authenticated-scope process metadata export');
 if(/postgres(?:ql)?:\/\/|\/Users\/|secret_access_key|access_token|password/i.test(body.toString()))throw Error('Private content in production metadata');
 await writeFile(resolve(root,'dist/data/production-v2.json'),body);
}
for(const [from,to] of [['view.js','research-v2.js'],['view.css','research-v2.css']])await writeFile(resolve(root,'dist',to),await readFile(resolve(root,'src/research-v2',from)));
console.log('Research v2 display assets built; optional process metadata copied. Six-case pilot data and research results unchanged.');
