// Read only the exporter's authenticated future registration projection.
// Raw RESEARCH_SPEC declarations, similarity and current candidate files are not authority.
const sha=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x);
export function registeredEdges(catalog,records){
 const included=new Map(records.map(r=>[r.id,r])),raw=new Map(catalog.records.map((r,i)=>[r.record_id,{r,i}]));
 const output=[];
 for(const target of records){
  const {r,i}=raw.get(target.id),l=r.registered_lineage;
  if(!l||l.status!=='RECORDED_AT_REGISTRATION')continue;
  if(l.schema_version!=='registered-lineage-public-v1'||l.reference_authentication!=='CURRENT_PUBLIC_REVIEW_VERSION_AND_PACKET'
   ||l.definition_hash!==r.provenance.definition_hash||l.strategy_sha256!==r.definition.research_spec?.strategy_sha256
   ||!['strategy_sha256','declaration_hash','capture_id','knowledge_snapshot_hash'].every(k=>sha(l[k]))
   ||l.historical_backfill!==false||l.follow_up_executed!==false||l.independent_evidence!==false
   ||!Array.isArray(l.lesson_references))continue;
  const seen=new Set();
  for(const [j,ref] of l.lesson_references.entries()){
   const source=included.get(ref.record_id),original=raw.get(ref.record_id);
   if(!source||source.id===target.id||seen.has(source.id)||!sha(ref.review_hash)
    ||source.packet!==ref.packet_sha256||original.r.review.packet_sha256!==ref.packet_sha256
    ||!['DECLARED_QUALITATIVE_LESSON_USE','DECLARED_COMPARISON_REFERENCE'].includes(ref.relation))continue;
   seen.add(source.id);
   const use=ref.relation==='DECLARED_QUALITATIVE_LESSON_USE';
   const src={record_id:target.id,pointer:`/records/${i}/registered_lineage/lesson_references/${j}`,packet_sha256:target.packet};
   const other={record_id:source.id,pointer:`/records/${original.i}/review/general_lesson`,packet_sha256:source.packet};
   output.push({from:use?source.sections.lesson:target.sections.hypothesis,to:use?target.sections.hypothesis:source.sections.hypothesis,
    relation:use?'methodology_reference':'registered_comparison',basis:'AUTHENTICATED_PREREGISTERED_QUALITATIVE_REFERENCE',
    source:src,sources:[src,other],registered_relation:ref.relation,
    registration:{registered_at:l.registered_at,declared_at:l.declared_at,snapshot_captured_at:l.snapshot_captured_at,
     capture_id:l.capture_id,knowledge_snapshot_hash:l.knowledge_snapshot_hash,declaration_hash:l.declaration_hash,
     source_review_hash:ref.review_hash},
    note:use?'새 실험 등록 전에 이 교훈의 활용을 선언한 기록입니다. 실제 읽기·인과 영향·독립 증거·앞 제안의 실행을 입증하지 않습니다.':'새 실험 등록 전에 비교 대상으로 선언한 기록입니다. 비교 실험의 수행·교훈 활용·실증 지지를 뜻하지 않습니다.'});
  }
 }
 return output;
}
