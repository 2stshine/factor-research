const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises'),assert=require('node:assert/strict');
const root=require('node:path').resolve(__dirname,'..');const output=process.env.OBSERVATORY_EVIDENCE_DIR||require('node:path').join(root,'output/semantics-ui');
const base=process.env.OBSERVATORY_PREVIEW_URL||'http://127.0.0.1:4173',checks=[],errors=[];
(async()=>{const browser=await chromium.launch({headless:true});try{
await fs.mkdir(output,{recursive:true});
const p=await browser.newPage({viewport:{width:1180,height:757}});p.on('pageerror',e=>errors.push(e.message));
await p.goto(base+'/#map',{waitUntil:'networkidle'});await p.locator('.rmn-stage').waitFor();
const box=await p.locator('.rmn-stage').boundingBox();assert(box.y<350,JSON.stringify(box));assert(box.width>800);assert(await p.locator('.rmn-detail').isHidden());
assert.equal(await p.locator('[data-rmn-node]').count(),531);checks.push('1180×757: full-width graph begins above 350px; detail collapsed; 531 nodes');
await p.screenshot({path:output+'/batch1-map-laptop.png'});
await p.locator('[data-rmn-panel-toggle]').click();await p.locator('[data-rmn-section="hypothesis"]').click();
assert.match(await p.locator('.rmn-content').innerText(),/선언된 추가 재무입력 없음/);assert.match(await p.locator('.rmn-content').innerText(),/\/records\/176\/definition\/inputs/);
const influence=p.locator('.rmn-connections button').filter({hasText:'명시적 교훈 활용'});await influence.focus();await p.keyboard.press('Enter');
assert.match(await p.locator('.rmn-edge-endpoints').innerText(),/229[\s\S]*→[\s\S]*230/);assert(!((await p.locator('.rmn-edge-endpoints').innerText()).includes('↔')));
assert.equal(await p.locator('.rm-source').count(),2);checks.push('Financial needs declaration semantics with pointer; keyboard adjacent relation opens directed 229→230 source detail');
await p.locator('[data-rmn-panel-close]').click();assert(await p.locator('.rmn-detail').isHidden());
await p.goto(base+'/#overview',{waitUntil:'networkidle'});assert(!((await p.locator('main').innerText()).includes('가설과 부합')));assert((await p.locator('main').innerText()).includes('교훈과 부합'));assert((await p.locator('main').innerText()).includes('이전 노출 22건'));
checks.push('Overview lesson stance and historical exposure boundary');
await p.goto(base+'/#regimes',{waitUntil:'networkidle'});assert.equal(await p.locator('#regime-study option').count(),1);assert.equal(await p.locator('#regime-results > .table-wrap table tbody tr').count(),5);assert.match(await p.locator('#regime-results > .table-wrap table tbody').innerText(),/미분류/);
assert.match(await p.locator('.input-readiness > summary').innerText(),/0\/39/);assert.equal(await p.locator('.input-readiness').getAttribute('open'),null);
await p.locator('.input-readiness > summary').click();await p.locator('.input-readiness .source > summary').click();assert.match(await p.locator('.input-readiness table').innerText(),/한국 산업생산 · 전년비/);assert.match(await p.locator('.input-readiness table').innerText(),/FMP_ASSUMED_KR_INDUSTRIAL_PRODUCTION_YOY/);
await p.locator('.input-readiness > summary').click();await p.screenshot({path:output+'/batch1-regimes-laptop.png'});
checks.push('Five coarse states; source snapshot vs Oct1 0/39 audit; folded human-labeled source table');
const real=JSON.parse(await fs.readFile(root+'/dist/data/research-catalog.json','utf8'));
async function fixture(catalog){const page=await browser.newPage({viewport:{width:1180,height:757}});page.on('pageerror',e=>errors.push(e.message));await page.route('**/data/research-catalog.json',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(catalog)}));return page;}
const none=structuredClone(real);for(const r of none.records)r.regimes={};none.counts.regime_records=0;
const z=await fixture(none);await z.goto(base+'/#regimes',{waitUntil:'networkidle'});assert.match(await z.locator('main').innerText(),/공개된 레짐 연구가 없습니다/);await z.goto(base+'/#overview',{waitUntil:'networkidle'});assert.match(await z.locator('main').innerText(),/레짐 진단이 수집된 연구가 없습니다/);await z.close();
const newer=structuredClone(real),newRecord={...structuredClone(newer.records.at(-1)),record_id:'synthetic-newest',campaign_id:'campaign-20261001-001',provenance:{...newer.records.at(-1).provenance,cycle:'cycle-0231-synthetic'},regimes:{}};newer.records.push(newRecord);newer.counts.released_records++;
const one=await fixture(newer);await one.goto(base+'/#overview',{waitUntil:'networkidle'});assert.equal(await one.locator('.featured [data-record]').getAttribute('data-record'),'synthetic-newest');await one.goto(base+'/#regimes',{waitUntil:'networkidle'});assert.equal(await one.locator('#regime-study option').count(),1);assert.notEqual(await one.locator('#regime-study').inputValue(),'synthetic-newest');await one.close();
newer.records.at(-1).regimes=structuredClone(real.records.at(-1).regimes);
const two=await fixture(newer);await two.goto(base+'/#regimes',{waitUntil:'networkidle'});assert.equal(await two.locator('#regime-study option').count(),2);await two.locator('#regime-study').selectOption(real.records.at(-1).record_id);assert.equal(await two.locator('#regime-study').inputValue(),real.records.at(-1).record_id);await two.close();
const missing=structuredClone(real),g=missing.records.at(-1).regimes;g.monthly=g.monthly.slice(0,18).map((r,i)=>({...r,regime:i<12?'UP_LOW':'UNKNOWN'}));g.regimes=[{regime:'UP_LOW',n_months:12,n_joint_usable_months:12,n_joint_usable_episodes:1,support:'INSUFFICIENT_SUPPORT',rank_ic:{mean:.1,ci95:null},top_minus_bottom:{mean:.01,ci95:null}}];
const u=await fixture(missing);await u.goto(base+'/#regimes',{waitUntil:'networkidle'});const row=u.locator('#regime-results > .table-wrap table tbody tr').filter({hasText:'미분류'});assert.equal(await row.locator('td').nth(1).innerText(),'6');assert.equal(await row.locator('td').nth(4).innerText(),'—');await u.close();checks.push('Browser fixtures: zero/one/two regime studies, newer non-regime latest, 12 known+6 UNKNOWN retained');
for(const route of ['factors','lessons','studies','method','comparison']){await p.goto(base+'/#'+route,{waitUntil:'networkidle'});assert((await p.locator('main').innerText()).length>100);}
await p.goto(base+'/#comparison',{waitUntil:'networkidle'});assert.match(await p.locator('main').innerText(),/0 \/ 196/);
for(const route of ['overview','regimes','map']){await p.setViewportSize({width:390,height:844});await p.goto(base+'/#'+route,{waitUntil:'networkidle'});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
await p.screenshot({path:output+'/batch1-map-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
await fs.writeFile(output+'/batch1-browser-verification.json',JSON.stringify({checks,errors,laptop_graph:box},null,2));console.log(JSON.stringify({checks,errors,laptop_graph:box},null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
