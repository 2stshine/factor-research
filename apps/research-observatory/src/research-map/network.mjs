// Cross-cycle relationships are projected only from authenticated frozen records.
const cycle=r=>Number(r.provenance.cycle.match(/cycle-(\d+)/)?.[1]);
const normalized=s=>String(s||'').replaceAll('\r\n','\n').trim();
export function createNetwork(catalog,records,canonicalEdges){
 const byId=new Map(catalog.records.map((r,i)=>[r.record_id,{r,i}])),approved=new Set(records.map(r=>r.id));
 const nodes=[],edges=[],categories=['quality','value','earnings','momentum','other'];
 const names={quality:'재무 건전성 · 측정',value:'가치 · 가격 대비',earnings:'이익 · 수익성',momentum:'가격 흐름 · 반전',other:'거래활동 · 기타'};
 const groups=categories.map(category=>({category,label:names[category],rows:records.filter(p=>byId.get(p.id).r.definition.category===category).sort((a,b)=>cycle(byId.get(a.id).r)-cycle(byId.get(b.id).r))}));
 const unknown=records.filter(p=>!categories.includes(byId.get(p.id).r.definition.category));if(unknown.length)groups.push({category:'unknown',label:'미분류',rows:unknown});
 if(records.some(p=>byId.get(p.id).r.review.follow_up.execution!=='PROPOSED_NOT_RUN'))throw Error('Network execution semantics require review for new follow-up status');
 const refs=(r,key)=>{const {i}=byId.get(r.record_id);return {record_id:r.record_id,packet_sha256:r.provenance.packet_sha256,pointer:`/records/${i}/${key}`};};
 const clusters=[];let y=2200;const anchors=[[620,650,480],[540,1620,265],[1980,1610,245],[1270,1670,300],[1800,650,450],[1250,2100,100]];let gi=0;
 for(const group of groups){
  const [cx,centerY,radius]=anchors[gi++];clusters.push({id:group.category,label:group.label,x:cx-radius-90,y:centerY-radius-100,width:radius*2+180,height:radius*2+200});
  group.rows.forEach((p,j)=>{const r=byId.get(p.id).r,angle=j*2.3999632297,rad=radius*Math.sqrt((j+.4)/Math.max(1,group.rows.length)),x=cx+Math.cos(angle)*rad-45,cy=centerY+Math.sin(angle)*rad;
   for(const [kind,section,dx,dy] of [['hypothesis','hypothesis',0,0],['lesson','lesson',45,22],['question','followup',90,0]]){
    nodes.push({id:p.sections[section],case_id:r.record_id,kind,cycle:cycle(r),factor:r.factor_name,x:x+dx,y:cy+dy,category:group.category,source:refs(r,kind==='hypothesis'?'definition/hypothesis':kind==='lesson'?'review/general_lesson':'review/follow_up'),execution:kind==='question'?r.review.follow_up.execution:null});
   }
   edges.push({id:'interpretation:'+r.record_id,from:p.sections.hypothesis,to:p.sections.lesson,type:'within_case',label:'같은 실험의 검토 교훈',basis:'REVIEW_STRUCTURE_NOT_PROOF',sources:[refs(r,'definition/hypothesis'),refs(r,'review/general_lesson')],note:'가설에서 교훈으로 이어지는 기록 구조입니다. 가설의 성공이나 인과 입증을 뜻하지 않습니다.'});
   edges.push({id:'proposal:'+r.record_id,from:p.sections.lesson,to:p.sections.followup,type:'proposed_question',label:'다음 질문 제안 · 미실행',basis:'SAME_REVIEW_PROPOSAL_NOT_EXECUTION',sources:[refs(r,'review/general_lesson'),refs(r,'review/follow_up')],execution:r.review.follow_up.execution,note:'같은 검토에 기록된 제안입니다. 후속 실험이 실행됐다는 연결이 아닙니다.'});
  });
 }
 for(const e of canonicalEdges.filter(e=>e.relation==='methodology_reference')){
  const registered=!!e.registration;
  edges.push({id:'influence:'+e.from+'>'+e.to,from:e.from,to:e.to,type:'lesson_use',label:registered?'등록 시 선언한 교훈 활용':'명시적 교훈 활용',basis:e.basis,
   sources:e.sources||[e.source,refs(byId.get(nodes.find(n=>n.id===e.from).case_id).r,'review/lesson_key')],
   quote:e.basis==='EXACT_LESSON_KEY_REFERENCE'?byId.get(e.source.record_id).r.definition.data_notes:undefined,
   ...(registered?{registration:e.registration}:{}),
   note:registered?'새 실험 등록 전에 이 교훈의 활용을 선언한 기록입니다. 실제 읽기·인과 영향·독립 증거·앞 제안의 실행을 입증하지 않습니다.':'계산·측정 해석의 교훈을 활용했다는 명시적 기록입니다. 앞 연구의 follow-up을 실행했거나 경제적 가설을 입증했다는 뜻이 아닙니다.'});
 }
 const fields=['hypothesis','expected_relationship','mechanism','data_notes','falsification'];
 const mentions=new Map();
 for(const a of records){const r=byId.get(a.id).r;for(const b of records){if(a.id===b.id)continue;const target=byId.get(b.id).r.factor_name;
  for(const field of fields){const raw=r.definition[field],value=typeof raw==='string'?raw:JSON.stringify(raw||'');const re=new RegExp('(^|[^a-zA-Z0-9_])'+target+'(?=$|[^a-zA-Z0-9_])','g');
   if(re.test(value)){const key=a.id+'>'+b.id;if(!mentions.has(key))mentions.set(key,{id:'reference:'+key,from:a.sections.hypothesis,to:b.sections.hypothesis,type:'declared_reference',label:'원문에 명시한 비교·참조',basis:'EXACT_FACTOR_NAME_IN_FROZEN_NARRATIVE',sources:[],quotes:[],note:'다른 연구를 비교 대상으로 언급했습니다. 실제 비교 수행, 교훈의 영향, 실증 지지·반증을 주장하지 않습니다.'});const e=mentions.get(key);e.sources.push(refs(r,'definition/'+field));e.quotes.push({field,text:value});}
  }
 }}
 for(const e of canonicalEdges.filter(e=>e.relation==='registered_comparison')){
  const a=nodes.find(n=>n.id===e.from).case_id,b=nodes.find(n=>n.id===e.to).case_id,key=a+'>'+b;
  if(mentions.has(key)){const prior=mentions.get(key);prior.sources.push(...e.sources);prior.registration=e.registration;}
  else mentions.set(key,{id:'reference:'+key,from:e.from,to:e.to,type:'declared_reference',label:'등록 시 선언한 비교·참조',basis:e.basis,sources:e.sources,quotes:[],registration:e.registration,note:e.note});
 }
 edges.push(...mentions.values());
 const formulas=new Map();for(const p of records){const r=byId.get(p.id).r,key=normalized(r.definition.source);if(!key)continue;if(!formulas.has(key))formulas.set(key,[]);formulas.get(key).push(p);}
 let repeatedGroups=0,variantMembers=0;
 for(const [source,list] of formulas){if(list.length<2)continue;repeatedGroups++;variantMembers+=list.length;
  for(let i=0;i<list.length;i++)for(let j=i+1;j<list.length;j++){const a=list[i],b=list[j],ra=byId.get(a.id).r,rb=byId.get(b.id).r;
   edges.push({id:'formula:'+a.id+'|'+b.id,from:a.sections.hypothesis,to:b.sections.hypothesis,type:'formula_variant',label:'동일 계산 코드 · 조건 비교',basis:'EXACT_NORMALIZED_SOURCE_PARAMS_SEPARATE',sources:[refs(ra,'definition/source'),refs(rb,'definition/source'),refs(ra,'definition/params'),refs(rb,'definition/params'),refs(ra,'definition/predicted_sign'),refs(rb,'definition/predicted_sign')],differences:[{case_id:a.id,params:ra.definition.params,predicted_sign:ra.definition.predicted_sign},{case_id:b.id,params:rb.definition.params,predicted_sign:rb.definition.predicted_sign}],note:'줄바꿈·바깥 공백만 정규화한 frozen compute source가 동일합니다. params·방향은 각각 보존합니다. 계산식이 같아도 동일 메커니즘·독립 재현·앞 실험의 영향은 입증하지 않습니다.'});
  }
 }
 // A reversible editorial navigation layer, off by default. Never an influence edge.
 for(const g of groups)for(let i=1;i<g.rows.length;i++){const a=g.rows[i-1],b=g.rows[i],ra=byId.get(a.id).r,rb=byId.get(b.id).r;edges.push({id:'category:'+a.id+'|'+b.id,from:a.sections.lesson,to:b.sections.lesson,type:'editorial_category',label:'같은 분류 · 시간상 이웃',basis:'EDITORIAL_LAYOUT_ASSOCIATION',sources:[refs(ra,'definition/category'),refs(rb,'definition/category')],note:'원문의 category가 같고 시간상 인접한 사례를 탐색 편의상 잇습니다. 사고 계보나 실증적 지지 관계가 아닙니다.'});}
 const ids=new Set(nodes.map(n=>n.id));for(const e of edges)if(!ids.has(e.from)||!ids.has(e.to)||e.sources.some(s=>!approved.has(s.record_id)))throw Error('Network refers outside released records');
 const counts=Object.fromEntries([...new Set(edges.map(e=>e.type))].map(t=>[t,edges.filter(e=>e.type===t).length]));
 const incident=new Set(edges.filter(e=>e.type==='lesson_use').flatMap(e=>[nodes.find(n=>n.id===e.from).case_id,nodes.find(n=>n.id===e.to).case_id]));
 return {schema_version:'shared-coordinate-research-network-v2',nodes,edges,clusters,width:2500,height:y,counts:{...counts,cases:records.length,hypotheses:records.length,lessons:records.length,questions:records.length,followups_executed:0,without_recorded_lesson_influence:records.length-incident.size,formula_groups:repeatedGroups,formula_members:variantMembers,reference_mentions:[...mentions.values()].reduce((n,e)=>n+e.quotes.length,0),cycle_min:Math.min(...nodes.map(n=>n.cycle)),cycle_max:Math.max(...nodes.map(n=>n.cycle))},principle:'Layout, formula equivalence and references are not causal or independent evidence. No proposed follow-up is marked executed.'};
}
