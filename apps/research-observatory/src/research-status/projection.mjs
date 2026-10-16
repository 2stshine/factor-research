import {validateSourceStructure} from './source-structure.mjs';
import {createHash} from 'node:crypto';
import {selectStudies,cycleOf,campaignEvidence,diagnosticCoverage,displayFreshness,reconcileCoarse} from './semantics.mjs';
export const digest=v=>createHash('sha256').update(v).digest('hex');
const normalized=s=>String(s||'').replaceAll('\r\n','\n').trim();
export function buildStatus(catalog,comparison,annotations,{catalogHash,displayAsOf,sourceStructure=null}){
 const records=catalog.records,ids=new Map(records.map(r=>[r.record_id,r]));
 if(ids.size!==records.length||catalog.counts.released_records!==records.length)throw Error('Released identity/count mismatch');
 if(records.some(r=>r.visibility!=='RELEASED_QUALITATIVE'||r.provenance?.authentication!=='CURRENT_RELEASE_STATE_AND_EXACT_PACKET_REBUILD'))throw Error('Only authenticated released records are allowed');
 if(annotations.schema_version!=='released-definition-annotations-v1'||annotations.scope!=='AUTHENTICATED_RELEASED_RECORDS_ONLY')throw Error('Annotation schema/scope mismatch');
 const domains=new Set(annotations.domains.map(d=>d.id)),notes=new Map();
 if(domains.size!==8)throw Error('Review changes to the eight declared exploration domains');
 for(const a of annotations.annotations){
  const r=ids.get(a.record_id);
  if(!r||r.provenance.definition_hash!==a.definition_hash||r.provenance.packet_sha256!==a.packet_sha256||notes.has(a.record_id))throw Error('Annotation immutable identity mismatch');
  if(!domains.has(a.domain)||!a.rationale||!a.source_pointers?.length||a.status!=='HUMAN_REVIEWED_DEFINITION_ONLY')throw Error('Reviewed definition-only annotation required');
  if(a.source_pointers.some(p=>!p.startsWith('/definition/')))throw Error('Outcome-driven annotation source is prohibited');
  for(const pointer of a.source_pointers){let value=r;for(const key of pointer.slice(1).split('/').map(x=>x.replaceAll('~1','/').replaceAll('~0','~'))){if(!value||typeof value!=='object'||!Object.hasOwn(value,key))throw Error('Unknown definition source pointer');value=value[key];}if(value==null||value==='')throw Error('Empty definition source pointer');}
  notes.set(a.record_id,a);
 }
 const groups=new Map(),rows=records.map((r,i)=>{
  const source=normalized(r.definition.source),template=source?digest(source):null;
  if(template){if(!groups.has(template))groups.set(template,[]);groups.get(template).push(r.record_id);}
  const original=r.definition.exploration_domain,annotation=notes.get(r.record_id),domain=original||annotation?.domain||null;
  if(domain&&!domains.has(domain))throw Error('Unknown declared domain requires review');
  return {record_id:r.record_id,cycle:cycleOf(r),factor_name:r.factor_name,definition_hash:r.provenance.definition_hash,packet_sha256:r.provenance.packet_sha256,
   catalog_pointer:'/records/'+i,category:r.definition.category||null,domain,domain_basis:original?'FROZEN_DECLARATION':annotation?'REVIEWED_SIDECAR':'NOT_RECORDED',
   mechanism_text_present:!!r.definition.mechanism?.trim(),falsification_text_present:!!r.definition.falsification?.trim(),
   inputs_declared:(r.definition.inputs||[]).length,financial_inputs_state:Array.isArray(r.definition.inputs)?(r.definition.inputs.length?'DECLARED':'NO_ADDITIONAL_FINANCIAL_INPUTS'):'NOT_RECORDED',raw_input_profile_collected:!!r.diagnostics?.input_quality?.data?.raw_input_profile?.length,
   template_id:template,params:r.definition.params||{},predicted_sign:r.definition.predicted_sign??null,rebalance_months:r.definition.rebalance_months??null};
 });
 const templates=[...groups].map(([id,members])=>({id,record_ids:members})).sort((a,b)=>b.record_ids.length-a.record_ids.length||a.id.localeCompare(b.id));
 const selected=selectStudies(catalog),releasedCampaigns=catalog.campaigns.filter(c=>c.released_records>0);
 const repeated=templates.filter(t=>t.record_ids.length>1);
 return {schema_version:'public-research-status-v1',scope:'AUTHENTICATED_RELEASED_RECORDS_ONLY',catalog_sha256:catalogHash,
  annotation_revision:annotations.revision,annotation_sha256:digest(JSON.stringify(annotations)),display_audit_as_of:displayAsOf,
  source_snapshot_as_of:catalog.as_of,source_refreshed:false,source_structure:sourceStructure?validateSourceStructure(sourceStructure,catalog,catalogHash):null,counts:{released:records.length,withheld:catalog.counts.withheld_records,
   reviewed:records.filter(r=>r.review_status==='REVIEWED_CURRENT').length,declared_domains:rows.filter(r=>r.domain_basis==='FROZEN_DECLARATION').length,
   sidecar_domains:rows.filter(r=>r.domain_basis==='REVIEWED_SIDECAR').length,unknown_domains:rows.filter(r=>!r.domain).length,
   mechanism_text:rows.filter(r=>r.mechanism_text_present).length,falsification_text:rows.filter(r=>r.falsification_text_present).length,
   input_list_present:rows.filter(r=>r.inputs_declared>0).length,financial_inputs_empty:rows.filter(r=>r.financial_inputs_state==='NO_ADDITIONAL_FINANCIAL_INPUTS').length,financial_inputs_unrecorded:rows.filter(r=>r.financial_inputs_state==='NOT_RECORDED').length,raw_input_profile_collected:rows.filter(r=>r.raw_input_profile_collected).length,
   templates:templates.length,repeated_template_groups:repeated.length,repeated_template_members:repeated.reduce((n,t)=>n+t.record_ids.length,0),
   regimes:selected.regimeStudies.length,confirmation_evaluated:records.filter(r=>campaignEvidence(catalog,r).evaluated).length,
   released_campaigns:releasedCampaigns.length,reused_campaigns:releasedCampaigns.filter(c=>c.oos?.evidence_class==='HISTORICAL_REUSED_WINDOW').length,
   revealed_campaigns:releasedCampaigns.filter(c=>c.oos?.status==='REVEALED').length},
  domains:annotations.domains.map(d=>({...d,count:rows.filter(r=>r.domain===d.id).length})),
  categories:[...new Set(rows.map(r=>r.category))].map(category=>({category,count:rows.filter(r=>r.category===category).length})),
  records:rows,templates,diagnostics:diagnosticCoverage(records),
  regimes:selected.regimeStudies.map(r=>({record_id:r.record_id,months:r.regimes.monthly.length,phase:r.regimes.phase,coarse:reconcileCoarse(r.regimes),
   detail_cells:Array.isArray(r.regimes.views?.regime_detail)?r.regimes.views.regime_detail.filter(x=>x.regime_detail!=='UNKNOWN').length:null,
   detail_display_supported:Array.isArray(r.regimes.views?.regime_detail)?r.regimes.views.regime_detail.filter(x=>x.regime_detail!=='UNKNOWN'&&x.support==='DESCRIPTIVE_SUPPORT_ONLY').length:null,
   macro_inputs:Object.keys(r.regimes.macro_views||{}).length,source_pointer:'/records/'+records.indexOf(r)+'/regimes'})),
  freshness:displayFreshness(catalog.regime_input_snapshot,displayAsOf),
  score_space:{status:'NOT_COMPUTED',correlation:null,effective_dimension:null,reason:'A common eligible stock-month score matrix bound to the frozen definitions has not been supplied. Pairwise median correlations are not assumed PSD.'},
  historical_gold_current_identity:{current_definitions:comparison?.factor_count??null,changed:comparison?.historical_definition_changed??null,unknown:comparison?.historical_definition_unknown??null},
  boundaries:['Template grouping does not reduce research trial or multiple-testing counts.','Missing annotation is not an unexplored economic domain.','Mechanism text is a hypothesis, not causal verification.','Current code, frozen trials and historical Gold definitions are not interchangeable.','No scores, new performance, sealed results or candidate-generation feed are added.']};
}
