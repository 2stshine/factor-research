// Public projection of an explicitly reviewed status sidecar. Never reads raw inputs.
const statuses=Object.freeze({score_inventory:'VALUES_OBSERVED_PIT_UNVERIFIED',raw_opens:'LOCAL_CANDIDATES_UNCERTIFIED',stock_accounting:'COMPONENT_TESTED_ADAPTERS_REQUIRED',calendar:'OFFICIAL_SESSION_TIMES_REQUIRED',benchmark:'OFFICIAL_OPEN_TR_SOURCE_REQUIRED',execution_bundle:'NOT_CERTIFIED_NOT_RUN'});
const fields=['schema_version','reviewed_at','comparison_id','plan_sha256','catalog_sha256','observations','evidence_kind'];
function exactKeys(value,keys){if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join('|')!==[...keys].sort().join('|'))throw Error('Unexpected readiness fields');}
function monthNumber(s){if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(s))throw Error('Invalid decision month');const [y,m]=s.split('-').map(Number);return y*12+m-1;}
function monthName(n){return `${Math.floor(n/12)}-${String(n%12+1).padStart(2,'0')}`;}
export function projectPreparation(comparison,review){
 if(comparison.schema_version!=='public-monthly-comparison-readiness-v1'||comparison.real_performance_computed!==false||comparison.actual_fill_verified!==false||comparison.independent_oos!==false||comparison.completed_comparisons!==0)throw Error('Not an unexecuted comparison');
 if(!Number.isInteger(comparison.factor_count)||comparison.factor_count<1||!Array.isArray(comparison.variants)||comparison.planned_comparisons!==comparison.factor_count*comparison.variants.length)throw Error('Invalid comparison counts');
 exactKeys(review,fields);
 if(review.schema_version!=='monthly-preparation-review-v1'||review.evidence_kind!=='MANUALLY_REVIEWED_LOCAL_READINESS'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(review.reviewed_at)||!Number.isFinite(Date.parse(review.reviewed_at)))throw Error('Unsupported preparation review');
 for(const key of ['comparison_id','plan_sha256','catalog_sha256'])if(review[key]!==comparison[key])throw Error('Stale preparation identity: '+key);
 for(const key of ['plan_sha256','catalog_sha256'])if(!/^[a-f0-9]{64}$/.test(review[key]))throw Error('Invalid identity hash');
 if(!Array.isArray(review.observations)||review.observations.length!==Object.keys(statuses).length)throw Error('Incomplete preparation states');
 const seen=new Set();for(const row of review.observations){exactKeys(row,['id','status']);if(!statuses[row.id]||statuses[row.id]!==row.status||seen.has(row.id))throw Error('Unsupported preparation state');seen.add(row.id);}
 const start=monthNumber(comparison.decision_start),end=monthNumber(comparison.decision_end);if(end<start||end-start>600)throw Error('Invalid comparison period');
 const lastOpen=monthName(end+2);if(!comparison.return_support_end?.startsWith(lastOpen))throw Error('Return support omits final valuation month');
 return {schema_version:'public-monthly-preparation-v1',evidence_kind:review.evidence_kind,reviewed_at:review.reviewed_at,comparison_id:comparison.comparison_id,plan_sha256:comparison.plan_sha256,catalog_sha256:comparison.catalog_sha256,
  real_performance_computed:false,execution_certified:false,actual_fill_verified:false,independent_oos:false,completed_comparisons:0,planned_comparisons:comparison.planned_comparisons,
  period:{signal_start:comparison.decision_start,signal_end:comparison.decision_end,signal_months:end-start+1,first_opening_month:monthName(start+1),final_opening_month:lastOpen,required_opening_months:end-start+2},
  observations:Object.keys(statuses).map(id=>({id,status:statuses[id]})),source_data_refreshed:false};
}
