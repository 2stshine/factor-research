import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {buildSourceStructure} from '../src/research-status/source-structure.mjs';
import {buildStatus,digest} from '../src/research-status/projection.mjs';
const here=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export async function buildResearchStatus(root=here,options={}){
 const config=JSON.parse(await readFile(resolve(root,'src/research-status/config.json'),'utf8'));
 const displayAsOf=options.displayAsOf||config.display_audit_as_of;
 const text=await readFile(resolve(root,'dist/data/research-catalog.json'),'utf8');
 let comparison=null;try{comparison=JSON.parse(await readFile(resolve(root,'dist/data/monthly-comparison.json'),'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
 const annotations=JSON.parse(await readFile(resolve(root,'src/research-status/annotations.json'),'utf8'));
 const catalog=JSON.parse(text),catalogHash=digest(text);
 const sourceStructure=buildSourceStructure(root,catalog,catalogHash);
 const status=buildStatus(catalog,comparison,annotations,{catalogHash,displayAsOf,sourceStructure});
 await writeFile(resolve(root,'dist/data/research-status.json'),JSON.stringify(status));
 const semantics=await readFile(resolve(root,'src/research-status/semantics.mjs'),'utf8');
 const exports=[...semantics.matchAll(/^export (?:function|const) (\w+)/gm)].map(m=>m[1]);
 await writeFile(resolve(root,'dist/research-semantics.js'),`(function(){'use strict';\n${semantics.replace(/^export /gm,'')}\nwindow.ResearchSemantics=Object.freeze({${exports.join(',')},displayAuditAsOf:${JSON.stringify(displayAsOf)}});\n})();\n`);
 await writeFile(resolve(root,'dist/research-status.js'),(await readFile(resolve(root,'src/research-status/source-view.js'),'utf8'))+'\n'+(await readFile(resolve(root,'src/research-status/view.js'),'utf8')));
 await writeFile(resolve(root,'dist/research-status.css'),await readFile(resolve(root,'src/research-status/view.css')));
 console.log(`Research status: ${status.counts.released} released; ${status.counts.unknown_domains} domains unrecorded; ${status.counts.templates} exact code templates; display audit ${displayAsOf}`);
 return status;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))await buildResearchStatus(here,{displayAsOf:process.argv[2]});
