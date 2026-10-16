import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp,cp,rm,access} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {stageSnapshot,publishSnapshot,syncSnapshot,generatedAssets} from './sync-snapshot.mjs';
const app=fileURLToPath(new URL('..',import.meta.url)),temp=await mkdtemp(resolve(tmpdir(),'snapshot-publish-test-'));
try{
 const root=resolve(temp,'app'),source=resolve(temp,'source');await mkdir(source,{recursive:true});await cp(resolve(app,'src'),resolve(root,'src'),{recursive:true});await mkdir(resolve(root,'dist/data'),{recursive:true});
 const research=JSON.parse(await readFile(resolve(app,'dist/data/research-catalog.json'),'utf8')),gold=JSON.parse(await readFile(resolve(app,'dist/data/gold-catalog.json'),'utf8'));
 await writeFile(resolve(source,'research-catalog.json'),JSON.stringify(research));await writeFile(resolve(source,'gold-catalog.json'),JSON.stringify(gold));await writeFile(resolve(source,'discovery-order.json'),JSON.stringify({...gold.discovery_order,factors:gold.factors.map(f=>f.discovery)}));
 await cp(resolve(app,'dist/data/monthly-comparison.json'),resolve(root,'dist/data/monthly-comparison.json'));
 for(const name of generatedAssets)await writeFile(resolve(root,'dist',name),Buffer.from('old served artifact '+name));
 await writeFile(resolve(root,'dist/user-note.txt'),'user-owned note');
 const previous=Object.fromEntries(await Promise.all(generatedAssets.map(async n=>[n,await readFile(resolve(root,'dist',n),'utf8')])));
 async function unchanged(){for(const n of generatedAssets)assert.equal(await readFile(resolve(root,'dist',n),'utf8'),previous[n]);}
 const staged=await stageSnapshot(root,source);await unchanged();assert.equal(Object.keys(staged.assets).length,generatedAssets.length);
 assert.equal(JSON.parse(staged.assets['data/research-map.json']).network.nodes.length,531);
 assert.equal(JSON.parse(staged.assets['data/research-status.json']).counts.released,177);
 assert.equal(JSON.parse(staged.assets['data/research-status.json']).counts.templates,146);
 // A late sidecar/graph failure must not replace the old served catalog first.
 const annotations=resolve(root,'src/research-status/annotations.json'),original=await readFile(annotations);
 const bad=JSON.parse(original);bad.annotations=[{record_id:'nonexistent'}];await writeFile(annotations,JSON.stringify(bad));
 await assert.rejects(stageSnapshot(root,source),/identity mismatch/);await unchanged();await writeFile(annotations,original);
 // A stale preparation review must also fail before any generated file changes.
 const reviewPath=resolve(root,'src/monthly-readiness/review.json'),reviewBytes=await readFile(reviewPath),staleReview=JSON.parse(reviewBytes);staleReview.plan_sha256='changed';await writeFile(reviewPath,JSON.stringify(staleReview));await assert.rejects(stageSnapshot(root,source),/Stale preparation identity/);await unchanged();await writeFile(reviewPath,reviewBytes);
 // Existing publication of any unknown/PENDING record is rejected before writes.
 const sealed=structuredClone(research);sealed.records[0].visibility='PENDING';await writeFile(resolve(source,'research-catalog.json'),JSON.stringify(sealed));
 await assert.rejects(stageSnapshot(root,source),/Unverified research row/);await unchanged();
 const privateField=structuredClone(research);privateField.password='SYNTHETIC_DO_NOT_PUBLISH';await writeFile(resolve(source,'research-catalog.json'),JSON.stringify(privateField));
 await assert.rejects(stageSnapshot(root,source),/sensitive/);await unchanged();await writeFile(resolve(source,'research-catalog.json'),JSON.stringify(research));
 // Concurrent generated-file changes are preserved, not overwritten.
 await writeFile(resolve(root,'dist/research-map.js'),'other user edit');await assert.rejects(publishSnapshot(root,staged),/Concurrent output change/);assert.equal(await readFile(resolve(root,'dist/research-map.js'),'utf8'),'other user edit');await writeFile(resolve(root,'dist/research-map.js'),previous['research-map.js']);
 const comparisonPath=resolve(root,'dist/data/monthly-comparison.json'),comparisonBytes=await readFile(comparisonPath);await writeFile(comparisonPath,'other user comparison');await assert.rejects(publishSnapshot(root,staged),/Concurrent comparison input/);await writeFile(comparisonPath,comparisonBytes);await unchanged();
 // Inject a failed file replacement after partial success; restore old served assets.
 let writes=0;await assert.rejects(publishSnapshot(root,staged,{write:async(p,b)=>{if(++writes===4)throw Error('SIMULATED_RENAME_FAILURE');await writeFile(p,b);}}),/SIMULATED_RENAME_FAILURE/);await unchanged();assert.equal(await readFile(resolve(root,'dist/user-note.txt'),'utf8'),'user-owned note');
 // The lock must block a second invocation without removing the first one's lock.
 await mkdir(resolve(root,'.snapshot-sync.lock'));await assert.rejects(syncSnapshot(root,source),e=>e.code==='EEXIST');await access(resolve(root,'.snapshot-sync.lock'));await rm(resolve(root,'.snapshot-sync.lock'),{recursive:true});
 const result=await syncSnapshot(root,source);assert.equal(result.files,generatedAssets.length);assert.equal(result.changed.length,generatedAssets.length);assert.equal(await readFile(resolve(root,'dist/user-note.txt'),'utf8'),'user-owned note');
 await assert.rejects(access(resolve(root,'.snapshot-sync.lock')),e=>e.code==='ENOENT');
 for(const name of generatedAssets)assert.deepEqual(await readFile(resolve(root,'dist',name)),staged.assets[name]);
 const repeated=await syncSnapshot(root,source);assert.equal(repeated.changed.length,0,'Idempotent build should avoid replacements');
 console.log('PASS: complete staging before writes; late validation/sealed/private failures preserve prior output; concurrent edits preserved; partial-write rollback; publication lock; deterministic idempotent generation of 11 assets.');
}finally{await rm(temp,{recursive:true,force:true});}
