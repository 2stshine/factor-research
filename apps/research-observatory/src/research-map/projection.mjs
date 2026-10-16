import {registeredEdges} from './registered-lineage.mjs';
import {createNetwork} from './network.mjs';
import {createHash} from 'node:crypto';
export const digest=s=>createHash('sha256').update(s).digest('hex');
const ptrEscape=s=>s.replaceAll('~','~0').replaceAll('/','~1');
export function project(catalog,thematic,{catalogHash,revision}){
 if(catalog.schema_version!=='private-research-catalog-v1')throw Error('Unsupported authenticated catalog');
 const nodes=[],edges=[],records=[],windows=new Map(),ids=new Set();let omitted=0;
 const add=n=>{if(ids.has(n.id))throw Error('Duplicate identity: '+n.id);ids.add(n.id);nodes.push(n);return n.id;};
 const edge=(from,to,relation,source,basis='EXACT_TYPED_FIELD')=>edges.push({from,to,relation,basis,source});
 const allIds=catalog.records.map(r=>r.record_id);if(new Set(allIds).size!==allIds.length)throw Error('Duplicate record identity');
 for(const [i,r] of catalog.records.entries()){
  if(r.visibility!=='RELEASED_QUALITATIVE'||r.review_status!=='REVIEWED_CURRENT'||r.review?.status!=='REVIEWED'){omitted++;continue;}
  if(r.provenance?.authentication!=='CURRENT_RELEASE_STATE_AND_EXACT_PACKET_REBUILD'||!r.provenance.packet_sha256||r.review.packet_sha256!==r.provenance.packet_sha256)throw Error('Unbound review: '+r.record_id);
  const base='/records/'+i,p=r.provenance.packet_sha256,root='case:'+r.record_id;
  const src=(path,evidence_id)=>({record_id:r.record_id,pointer:base+path,packet_sha256:p,...(evidence_id?{evidence_id}:{})});
  const refs=new Map();
  refs.set('hypothesis',{pointer:'/definition/hypothesis',label:'사전 가설',kind:'hypothesis'});
  for(const [phase,x] of Object.entries(r.performance||{}))if(x){
   if(x.evidence_id)refs.set(x.evidence_id,{pointer:'/performance/'+phase+'/metrics',label:phase==='discovery'?'탐색 구간 지표':'확인 지표 · 비용 집계는 탐색 구간',kind:'evidence'});
   for(const [j,c] of (x.checks||[]).entries())refs.set(c.evidence_id,{pointer:`/performance/${phase}/checks/${j}`,label:c.name,kind:'evidence'});
  }
  for(const [key,value] of Object.entries(r.diagnostics||{}))if(value)refs.set('diagnostic.discovery.'+key,{pointer:'/diagnostics/'+ptrEscape(key),label:key,kind:'evidence'});
  if(r.regimes)refs.set('diagnostic.discovery.regime_comparison',{pointer:'/regimes',label:'탐색 구간 레짐 진단',kind:'evidence'});
  const used=new Map();
  function evidence(eid){
   if(used.has(eid))return used.get(eid);
   const ref=refs.get(eid);if(!ref)throw Error('Unknown evidence: '+r.record_id+' '+eid);
   const id='evidence:'+p+':'+eid;
   if(!ids.has(id))add({id,type:ref.kind,label:ref.label,source:src(ref.pointer,eid)});
   used.set(eid,id);return id;
  }
  add({id:root,type:'case',label:r.factor_name,source:src('')});
  const sections={};
  for(const [key,path,label] of [['hypothesis','/definition/hypothesis','가설'],['observations','/review/observations','관측'],['lesson','/review/general_lesson','교훈'],['explanations','/review/explanations','대안 설명'],['limits','/review/unresolved','한계'],['followup','/review/follow_up','다음 질문']]){
   sections[key]=add({id:root+':'+key,type:key,label,source:src(path)});edge(root,sections[key],'contains',src(path));
  }
  r.review.observations.forEach((o,j)=>{const id=add({id:root+':observation:'+j,type:'observation',label:o.text,source:src('/review/observations/'+j)});edge(sections.observations,id,'contains',src('/review/observations/'+j));o.evidence_ids.forEach((e,k)=>edge(evidence(e),id,'cited_by',src(`/review/observations/${j}/evidence_ids/${k}`,e)));});
  r.review.explanations.forEach((e,j)=>{const id=add({id:root+':explanation:'+e.id,type:'explanation',label:e.claim,source:src('/review/explanations/'+j)});edge(sections.explanations,id,'contains',src('/review/explanations/'+j));for(const [key,relation] of [['supporting_evidence','supports_explanation'],['opposing_evidence','opposes_explanation']])e[key].forEach((ref,k)=>edge(evidence(ref),id,relation,src(`/review/explanations/${j}/${key}/${k}`,ref)));});
  r.review.mechanism_assessment.forEach((a,j)=>{const id=add({id:root+':assessment:'+a.link,type:'assessment',label:a.reason||a.link,status:a.assessment,source:src('/review/mechanism_assessment/'+j)});a.evidence_ids.forEach((e,k)=>edge(evidence(e),id,'cited_by',src(`/review/mechanism_assessment/${j}/evidence_ids/${k}`,e)));});
  const memberships=[];
  for(const t of thematic.themes){
   let path=null;if(t.selector.startsWith('mechanism:')){const j=r.review.mechanism_assessment.findIndex(a=>a.link===t.selector.split(':')[1]);if(j>=0)path='/review/mechanism_assessment/'+j;}
   else if(t.selector==='missing_evidence'&&r.review.missing_evidence?.length)path='/review/missing_evidence';
   else if(t.selector==='known_window'&&r.performance.discovery?.discovery_signal_period?.start)path='/performance/discovery/discovery_signal_period';
   if(path){memberships.push(t.id);edge('theme:'+t.id,sections.lesson,'about',src(path),'EDITORIAL_TYPED_RULE');}
  }
  if(!memberships.length){memberships.push('unclassified');edge('theme:unclassified',sections.lesson,'about',src('/review'),'EDITORIAL_TYPED_RULE');}
  const recordWindows=[];
  for(const [phase,period] of [['discovery',r.performance.discovery?.discovery_signal_period],['confirmation',r.performance.confirmation?.oos_signal_period]])if(period?.start&&period?.end){
   const key=phase+':'+period.start+':'+period.end;
   if(!windows.has(key))windows.set(key,{id:'window:'+key,type:'window',label:`${phase} ${period.start} → ${period.end}`,phase,start:period.start,end:period.end,records:[]});
   windows.get(key).records.push(r.record_id);recordWindows.push('window:'+key);edge(root,'window:'+key,'uses_calendar_window',src(`/performance/${phase}/${phase==='discovery'?'discovery_signal_period':'oos_signal_period'}`),'EXACT_CALENDAR_PERIOD_NOT_INDEPENDENCE');
  }
  records.push({id:r.record_id,packet:p,review_basis:r.provenance.review_basis,lesson_key:r.review.lesson_key,factor:r.factor_name,cycle:r.provenance.cycle,sections,themes:memberships,windows:recordWindows,evidence:Object.fromEntries(used),source:src('')});
 }
 const themes=[...thematic.themes,{id:'unclassified',title:'아직 분류되지 않은 교훈',short:'미분류',question:'어떤 질문에 연결할지 검토가 필요합니다.',color:'#8993a4'}];
 for(const t of themes)add({id:'theme:'+t.id,type:'theme',label:t.title,source:{mapping_version:thematic.version,selector:t.selector||'fallback'}});
 for(const w of windows.values())add(w);
 // Exact references to another existing lesson key only. This is methodology reuse, never empirical support.
 for(const a of records){const r=catalog.records.find(r=>r.record_id===a.id);for(const b of records)if(a.id!==b.id&&r.definition.data_notes?.includes(b.lesson_key))edge(b.sections.lesson,a.sections.hypothesis,'methodology_reference',a.source.pointer?{...a.source,pointer:a.source.pointer+'/definition/data_notes'}:a.source,'EXACT_LESSON_KEY_REFERENCE');}
 for(const e of registeredEdges(catalog,records)){
  const prior=edges.find(x=>x.from===e.from&&x.to===e.to&&x.relation===e.relation);
  if(prior){prior.sources=[prior.source,...e.sources];prior.registration=e.registration;prior.registered_relation=e.registered_relation;}
  else edges.push(e);
 }
 const ws=[...windows.values()];for(let i=0;i<ws.length;i++)for(let j=i+1;j<ws.length;j++)if(ws[i].phase===ws[j].phase&&ws[i].start<=ws[j].end&&ws[j].start<=ws[i].end)edge(ws[i].id,ws[j].id,'calendar_overlap',{periods:[ws[i].id,ws[j].id]},'EXACT_CALENDAR_INTERVAL');
 for(const e of edges)if(!ids.has(e.from)||!ids.has(e.to))throw Error('Dangling graph edge');
 return {schema_version:'reviewer-research-map-v1',purpose:'RESEARCH_REVIEW_ONLY_NOT_CANDIDATE_INPUT',as_of:catalog.as_of,revision,catalog_sha256:catalogHash,mapping_version:thematic.version,counts:{released:catalog.counts.released_records,included:records.length,omitted_not_current:omitted,withheld:catalog.counts.withheld_records,lessons:new Set(records.map(r=>r.lesson_key)).size,campaigns:new Set(records.map(r=>r.id.split('/')[0])).size,independent_replications:null},themes,records,windows:ws,nodes,edges,network:createNetwork(catalog,records,edges)};
}
