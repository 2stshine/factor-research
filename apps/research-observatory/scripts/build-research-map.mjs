import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {project,digest} from '../src/research-map/projection.mjs';
const here=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export async function buildResearchMap(root=here){
 const text=await readFile(resolve(root,'dist/data/research-catalog.json'),'utf8');
 const mapping=JSON.parse(await readFile(resolve(root,'src/research-map/themes.json'),'utf8'));
 const revision=JSON.parse(await readFile(resolve(root,'src/research-map/snapshot.json'),'utf8')).revision;
 const graph=project(JSON.parse(text),mapping,{catalogHash:digest(text),revision});
 await mkdir(resolve(root,'dist/data'),{recursive:true});
 await writeFile(resolve(root,'dist/data/research-map.json'),JSON.stringify(graph));
 await writeFile(resolve(root,'dist/research-map.js'),(await readFile(resolve(root,'src/research-map/network-view.js'),'utf8'))+'\n'+(await readFile(resolve(root,'src/research-map/view.js'),'utf8')));
 for(const [src,dest] of [['view.css','research-map.css']])await copyFile(resolve(root,'src/research-map',src),resolve(root,'dist',dest));
 console.log(`Research map: ${graph.counts.included} reviewed cases, ${graph.nodes.length} nodes, ${graph.edges.length} explicit edges`);
 return graph;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))await buildResearchMap();
