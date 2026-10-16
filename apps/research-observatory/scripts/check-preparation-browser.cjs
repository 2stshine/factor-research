const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base=process.env.OBSERVATORY_PREVIEW_URL||'http://127.0.0.1:4173',output=process.env.OBSERVATORY_EVIDENCE_DIR||path.join(root,'output/preparation-ui');
(async()=>{const browser=await chromium.launch({headless:true}),checks=[],errors=[];try{
 await fs.mkdir(output,{recursive:true});const page=await browser.newPage({viewport:{width:1180,height:850}});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/#comparison',{waitUntil:'networkidle'});await page.locator('#comparison-preparation').waitFor();
 assert.equal(await page.locator('[data-preparation-stage]').count(),6);assert.match(await page.locator('#comparison-preparation').innerText(),/강제 청산 매도·그 청산 비용은 계획에 포함하지 않습니다/);assert.match(await page.locator('main').innerText(),/0 \/ 196/);
 assert.match(await page.locator('#comparison-preparation').innerText(),/2018-04–2026-07.*100개/);
 assert.match(await page.locator('[data-preparation-stage="score_inventory"]').innerText(),/당시 사용 가능성은 미검증/);
 assert.match(await page.locator('[data-preparation-stage="stock_accounting"]').innerText(),/합성 테스트 통과/);
 checks.push('Six input-preparation stages; 0/196 performance; final July2026 opening; synthetic tests separate from real inputs');
 await page.locator('#comparison-preparation details>summary').focus();await page.keyboard.press('Enter');assert.match(await page.locator('#comparison-preparation details').innerText(),/별도 사전등록/);
 assert.match(await page.locator('#comparison-preparation details').innerText(),/초기 구간을 채우지 못합니다/);checks.push('Keyboard exposes official access/definition blockers and protocol-change boundary');
 await page.locator('#comparison-search').fill('no-matching-factor');assert.match(await page.locator('#comparison-factor-results').innerText(),/검색 결과가 없습니다/);await page.locator('#comparison-search').fill('');assert.equal(await page.locator('#comparison-factor-results tbody tr').count(),49);
 for(const width of [1180,768,390]){await page.setViewportSize({width,height:850});await page.evaluate(()=>scrollTo(0,0));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:output+'/preparation-'+width+'.png',fullPage:width===390});}checks.push('Existing 49-factor search preserved; 1180/768/390 widths without page overflow');
 const actual=JSON.parse(await fs.readFile(path.join(root,'dist/data/monthly-preparation.json'),'utf8'));const bad=await browser.newPage();bad.on('pageerror',e=>errors.push(e.message));
 await bad.route('**/data/monthly-preparation.json',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({...actual,plan_sha256:'STALE'})}));await bad.goto(base+'/#comparison',{waitUntil:'networkidle'});assert.match(await bad.locator('main').innerText(),/추가 점검을 불러오지 못했습니다/);assert.equal(await bad.locator('[data-preparation-stage]').count(),0);assert.match(await bad.locator('main').innerText(),/0 \/ 196/);await bad.close();checks.push('Stale plan fails closed while original comparison status stays available');
 assert.deepEqual(errors,[]);await fs.writeFile(output+'/preparation-browser-verification.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks,errors},null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
