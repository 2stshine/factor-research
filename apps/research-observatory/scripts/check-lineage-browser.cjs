// Synthetic future records stay in intercepted browser responses, never dist.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
const base=process.env.OBSERVATORY_PREVIEW_URL||'http://127.0.0.1:4322',root=path.resolve(__dirname,'..');
const output=process.env.OBSERVATORY_EVIDENCE_DIR||path.join(root,'output/lineage-ui');
(async()=>{
 const {project,digest}=await import('../src/research-map/projection.mjs');
 const raw=await fs.readFile(path.join(root,'dist/data/research-catalog.json'),'utf8'),catalog=JSON.parse(raw);
 const original=JSON.parse(await fs.readFile(path.join(root,'dist/data/research-map.json'),'utf8'));
 const themes=JSON.parse(await fs.readFile(path.join(root,'src/research-map/themes.json'),'utf8'));
 const target=catalog.records.find(r=>r.provenance.cycle.startsWith('cycle-0230-')),source=catalog.records.find(r=>r.provenance.cycle.startsWith('cycle-0229-'));
 const browser=await chromium.launch({headless:true}),checks=[],errors=[];
 try{
  for(const variant of ['legacy','DECLARED_QUALITATIVE_LESSON_USE','DECLARED_COMPARISON_REFERENCE']){
   const c=structuredClone(catalog),r=c.records.find(r=>r.record_id===target.record_id);
   if(variant!=='legacy')r.registered_lineage={schema_version:'registered-lineage-public-v1',status:'RECORDED_AT_REGISTRATION',reference_authentication:'CURRENT_PUBLIC_REVIEW_VERSION_AND_PACKET',
    definition_hash:r.provenance.definition_hash,strategy_sha256:r.definition.research_spec.strategy_sha256,declaration_hash:'d'.repeat(64),capture_id:'a'.repeat(64),knowledge_snapshot_hash:'c'.repeat(64),
    registered_at:'2030-01-01T00:02:00Z',declared_at:'2030-01-01T00:01:00Z',snapshot_captured_at:'2030-01-01T00:00:00Z',historical_backfill:false,follow_up_executed:false,independent_evidence:false,withheld_reference_count:0,
    lesson_references:[{record_id:source.record_id,packet_sha256:source.provenance.packet_sha256,review_hash:'b'.repeat(64),relation:variant}]};
   const body=JSON.stringify(c),graph=project(c,themes,{revision:original.revision,catalogHash:digest(body)});
   const ctx=await browser.newContext({viewport:{width:1180,height:850}}),p=await ctx.newPage();p.on('pageerror',e=>errors.push(e.message));
   await p.route('**/data/research-catalog.json',route=>route.fulfill({contentType:'application/json',body}));
   await p.route('**/data/research-map.json',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(graph)}));
   await p.goto(base+'/#map',{waitUntil:'networkidle'});await p.locator('.rmn-stage').waitFor();
   await p.locator('#rmn-search').fill('230');await p.locator('.rmn-search-results button').first().click();await p.locator('[data-rmn-section="hypothesis"]').click();
   assert.equal(await p.locator('[data-rmn-node]').count(),531);
   const detail=await p.locator('.rmn-content').innerText();
   if(variant==='legacy')assert.match(detail,/NOT_RECORDED/);
   else{
    assert.match(detail,/현재 공개 버전과 일치하는 참조 1개/);
    const edge=graph.network.edges.find(e=>e.registration);
    const exact=p.locator(`[data-rmn-edge-select="${edge.id}"]`);assert(await exact.count());await exact.focus();await p.keyboard.press('Enter');
    assert.match(await p.locator('.rmn-content').innerText(),/등록 때 보존한 참조/);
    assert.match(await p.locator('.rmn-content').innerText(),/2030-01-01T00:02:00Z/);
    assert.match(await p.locator('.rmn-panel-top').innerText(),variant.includes('COMPARISON')?/등록 시 선언한 비교/:/등록 시 선언한 교훈/);
    const endpoints=await p.locator('.rmn-edge-endpoints').innerText();assert(endpoints.includes('229')&&endpoints.includes('230'));
    assert.equal(await p.locator('.rmn-relation-direction').innerText(),'→');
    assert.match(endpoints,variant.includes('COMPARISON')?/230[\s\S]*229/:/229[\s\S]*230/);
   }
   for(const width of [768,390]){await p.setViewportSize({width,height:844});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));}
   checks.push(variant+': all nodes, details, keyboard relationship and responsive boundary');await ctx.close();
  }
  assert.deepEqual(errors,[]);await fs.mkdir(output,{recursive:true});await fs.writeFile(path.join(output,'lineage-browser-verification.json'),JSON.stringify({checks,errors,synthetic_fixtures_only:true},null,2));console.log(JSON.stringify({checks,errors}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
