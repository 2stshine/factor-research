"""Build new exact multiyear features while preserving the old frozen inputs."""
from pathlib import Path
import pandas as pd
from engine import reference_library as base, reference_multiyear_inputs as multi
from engine import reference_expansion_100 as lib
from scripts.publish_reference_expansion import load_input,load_json,save_json,sha
from engine.research_generation import digest

ROOT=Path('output/phenomena/reference-expansion-100-20261003')
SOURCE=Path('output/phenomena/reference-expansion-20261003/build-v2')

def run():
    out=ROOT/'financial-diversity'
    out.mkdir(parents=True,exist_ok=True)
    if (out/'input-evidence.json').exists():
        print('Completed input already present',flush=True)
        return
    identity,_=load_input(SOURCE)
    evidence=load_json(SOURCE/'source-evidence.json')
    path=SOURCE/'financial-features.parquet'
    if sha(path)!=evidence['financial_features_file_sha256']:
        raise ValueError('Frozen input changed')
    expanded,meta=multi.attach(pd.read_parquet(path),evidence['financial_source'])
    expanded.asset_id=expanded.asset_id.astype(str)
    features=[c for c in expanded if c.startswith(('fy_','prev_fy_','fy2_','fy3_','fy4_','fy5_')) and pd.api.types.is_numeric_dtype(expanded[c])]
    p=identity[[*base._BASE,'market_cap']].merge(expanded[['asset_id','date','multiyear_known_at',*features]],on=['asset_id','date'],validate='one_to_one')
    p.known_at=pd.concat([pd.to_datetime(p.known_at,utc=True),pd.to_datetime(p.multiyear_known_at,utc=True)],axis=1).max(axis=1)
    p=p.drop(columns='multiyear_known_at')
    p.to_parquet(out/'input.parquet',index=False)
    source_evidence=dict(parent_evidence_sha256=digest(evidence),parent_financial_sha256=sha(path),
        multiyear=meta,input_file_sha256=sha(out/'input.parquet'),input_sha256=lib.input_digest(p),
        role='MEASUREMENT_CONTROL',forward_labels_read=False,legacy_gold_used=False)
    save_json(out/'input-evidence.json',source_evidence)
    for ref,v in lib.financial_values(p).items():
        s=p.loc[v.notna()]
        print(dict(reference=ref,rows=len(s),assets=s.asset_id.nunique(),months=s.date.nunique()),flush=True)

if __name__=='__main__':run()
