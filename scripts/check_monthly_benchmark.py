"""Inspect the exact frozen-plan benchmark needs; no data collection or trading."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
from strategies.run_monthly_comparison import load_plan,save_new
from strategies.monthly_input_preparation import require
from strategies.monthly_benchmark_preparation import build_benchmark_draft
ROOT=Path(__file__).resolve().parents[1]


def prepare(plan_path,output,source_path=None,*,research_root=ROOT/'research'):
    plan,registered=load_plan(plan_path,research_root)  # sealed bounds before source reads
    require(not Path(output).exists(),'OUTPUT_EXISTS','Keep draft files immutable')
    months=list(map(str,pd.period_range(plan['bounds']['decision_start'],plan['bounds']['decision_end'],freq='M')))
    points,contract=[],None
    if source_path:
        source_path=Path(source_path);source=json.loads(source_path.read_text())
        require(source.get('schema_version')=='official-index-components-source-v1','SOURCE_SCHEMA','Unsupported index component source')
        contract=source.get('contract');points=source.get('points',[])
        require(isinstance(contract,dict) and contract.get('allowed_data_time')==plan['bounds']['allowed_data_time'],'DATA_BOUNDARY_MISMATCH','Source contract must preserve the frozen allowed data boundary')
        require(bool(source.get('source_files')),'SOURCE_HASH_REQUIRED','No unbound inputs')
        hashes={}
        for item in source['source_files']:
            path=Path(item['path']);path=path if path.is_absolute() else source_path.parent/path
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            require(actual==item.get('sha256'),'SOURCE_HASH_MISMATCH','Index source bytes changed')
            require(item['id'] not in hashes,'DUPLICATE_SOURCE','Source IDs must be unique')
            hashes[item['id']]=actual
        require(isinstance(contract,dict) and hashes==contract.get('source_hashes'),'SOURCE_BINDING_MISMATCH','All declared source hashes must be bound')
    result=build_benchmark_draft(months,points,contract)
    result['plan_sha256']=registered['plan_sha256']
    if source_path:result['source_manifest_sha256']=hashlib.sha256(source_path.read_bytes()).hexdigest()
    save_new(output,result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True,type=Path);p.add_argument('--sources',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    result=prepare(a.plan,a.output,a.sources)
    print(json.dumps({k:result[k] for k in ['status','execution_certified','required_opening_months','missing_opening_months','missing_windows','blockers']},ensure_ascii=False))
    return 2


if __name__=='__main__':raise SystemExit(main())
