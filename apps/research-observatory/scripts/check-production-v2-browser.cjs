const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path');
const base=(process.env.OBSERVATORY_PREVIEW_URL||'http://127.0.0.1:4173').replace(/\/$/,'');
const output=process.env.OBSERVATORY_EVIDENCE_DIR||'output/production-v2-ui';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL||undefined});const checks=[],errors=[];
 try{
  await fs.mkdir(output,{recursive:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(base+'/#research-v2',{waitUntil:'networkidle'});
  await page.locator('.v2-production-counts').waitFor();
  const metadata=await page.evaluate(()=>fetch('data/production-v2.json').then(response=>response.json()));
  assert.equal(metadata.oos_results_included,false);
  assert.equal(metadata.performance_metrics_included,false);
  assert.equal(metadata.production_lessons_included,false);
  const current=page.locator('.v2-production');
  const text=await current.innerText();
  assert(text.includes('중단 기록 '+metadata.counts.aborted_campaigns+'개'));
  assert(text.includes('후보가 등록된 캠페인 '+metadata.counts.campaigns_with_registered_candidates+'개'));
  assert(text.includes('완료된 팩터 연구나 새 승인으로 계산하지 않습니다'));
  assert.equal(await current.locator('tbody tr').count(),metadata.campaigns.length);
  for(const campaign of metadata.campaigns){
   const row=current.locator('tbody tr').filter({hasText:campaign.campaign_id}).filter({has:page.locator('th code',{hasText:new RegExp('^'+campaign.campaign_id+'$')})});
   assert.equal(await row.count(),1);
   if(campaign.process_stage==='ABORTED_BEFORE_REGISTRATION')assert((await row.innerText()).includes('후보 등록 전에 중단'));
  }
  assert.equal(await page.locator('.v2-case').count(),6);
  const boxes=await Promise.all([current.boundingBox(),page.locator('.page-heading').filter({hasText:'과거 파일럿'}).boundingBox()]);
  assert(boxes[0].y<boxes[1].y);
  checks.push('Current metadata precedes six unchanged pilot cards; campaign creation/abort not counted as completed research');
  assert(text.includes('다음 거래일 시가'));
  assert(text.includes('PIT_ASSUMED'));
  assert(text.includes('독립 비평'));
  assert(text.includes('정적 스냅샷'));
  checks.push('PIT assumption, month-end simulation vs next-open fills, independent review and static-snapshot boundaries visible');
  await current.locator('summary').click();
  assert(await current.locator('details').getAttribute('open')!==null);
  await current.locator('summary').click();
  const download=current.locator('a[download]');
  assert.equal(await download.getAttribute('href'),'./data/production-v2.json');
  assert.equal((await page.request.get(base+'/data/production-v2.json')).status(),200);
  checks.push('Disclosure toggle and process metadata download available');
  await current.screenshot({path:path.join(output,'production-desktop.png')});
  for(const width of [1180,768,390]){
   await page.setViewportSize({width,height:1000});
   await page.evaluate(()=>scrollTo(0,0));
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Page overflow at '+width);
   if(width===390){await page.screenshot({path:path.join(output,'production-mobile.png')});await current.screenshot({path:path.join(output,'production-mobile-section.png')});}
  }
  checks.push('1180/768/390 layouts have no horizontal page overflow');
  const fallback=await browser.newPage();fallback.on('pageerror',error=>errors.push(error.message));
  await fallback.route('**/data/production-v2.json',route=>route.fulfill({status:404,body:'Missing process snapshot'}));
  await fallback.goto(base+'/#research-v2',{waitUntil:'networkidle'});
  assert((await fallback.locator('.v2-production').innerText()).includes('과거 파일럿 결과로 현재 상태를 대신 판단하지 않습니다'));
  assert.equal(await fallback.locator('.v2-case').count(),6);
  await fallback.close();
  checks.push('Missing current snapshot fails visibly without hiding or repurposing pilot results');
  assert.deepEqual(errors,[]);
  const report={url:base+'/#research-v2',counts:metadata.counts,checks,errors,public_process_metadata_only:true};
  await fs.writeFile(path.join(output,'production-browser-verification.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
