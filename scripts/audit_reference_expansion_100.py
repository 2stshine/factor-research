"""Audit committed Gold and generate a candidate activation; never change pointers.

No outcome labels are read. A completed report requires actual database counts,
bound receipts, feature-only duplicate screening, and all three source quotas.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
from engine.reference_db import connect
from engine import reference_library as base, reference_gold as gold
from engine.reference_expansion_screen import completion, fingerprint
from engine.research_generation import digest
from scripts.publish_reference_expansion import load_json,save_json,sha,legacy_metadata_digest

ROOT=Path(__file__).resolve().parents[1]
EXP=ROOT/'output/phenomena/reference-expansion-100-20261003'
OLD=ROOT/'output/phenomena/reference-expansion-20261003/build-v2'

def verify_cache_job(item):
    dataset,path,pub,cache=item
    expected_sha=sha(path)
    frame=pd.read_parquet(path)
    gold.validate_publication(pub,gold.canonical_values(frame))
    if sha(path)!=expected_sha:raise ValueError('Source cache changed while being validated')
    destination=cache/(dataset+'.parquet')
    if destination.exists() and sha(destination)!=expected_sha:raise ValueError('Existing cache changed')
    if not destination.exists():shutil.copyfile(path,destination)
    if sha(destination)!=expected_sha:raise ValueError('Cache transport bytes changed')
    print(dict(canonical_cache_verified=dataset,rows=len(frame)),flush=True)
    return dataset,expected_sha

def inventory():
    original=load_json(ROOT/'research/phenomena/program-snapshots/45-references-20261003.json')
    old_ids={r for d in original['reference_datasets'] for r in d['reference_ids']}
    entries={d['dataset_id']:dict(d) for d in original['reference_datasets']}
    additions=[];publications={};paths={}
    for p in sorted(EXP.rglob('committed-verification.json')):
        if p.parent.name=='collection-cache':continue
        if not (p.parent/'publication.json').exists():continue
        pub=load_json(p.parent/'publication.json');receipt=load_json(p.parent/'receipt-applied.json');verified=load_json(p)
        if not verified['passed'] or verified['dataset_id']!=pub['dataset_id']:raise ValueError('Invalid committed checkpoint')
        dataset=pub['dataset_id']
        if dataset in publications:raise ValueError('Repeated committed publication')
        publications[dataset]=pub;paths[dataset]=p.parent/'values.parquet'
        entries[dataset]=dict(dataset_id=dataset,reference_ids=sorted(pub['definitions']))
        for ref,d in pub['definitions'].items():
            additions.append(dict(id=ref,quota_bucket=d['quota_bucket'],publication=pub,receipt=receipt))
    return original,old_ids,entries,additions,publications,paths

def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    original,old_ids,entries,additions,publications,paths=inventory()
    progress=completion(old_ids,additions)
    print(progress,flush=True)
    if not progress['complete']:raise ValueError('Actual committed count/source quotas incomplete')
    definitions={};summaries={};db_rows={}
    with connect() as conn,conn.cursor() as cur:
        legacy=legacy_metadata_digest(conn)
        for dataset in sorted(entries):
            cur.execute('SELECT metadata FROM gold.reference_dataset WHERE dataset_id=%s AND generation_id=%s',(dataset,gold.GENERATION))
            result=cur.fetchone()
            if not result:raise ValueError('Dataset missing from live Gold')
            pub=result[0]
            if dataset in publications and pub!=publications[dataset]:raise ValueError('Live metadata differs from receipt')
            publications[dataset]=pub
            if set(pub['definitions'])!=set(entries[dataset]['reference_ids']):raise ValueError('Live partition mismatch')
            cur.execute('SELECT reference_id,count(*) FROM gold.reference_value WHERE dataset_id=%s AND generation_id=%s GROUP BY reference_id',(dataset,gold.GENERATION))
            actual=dict(cur.fetchall())
            expected={v['reference_id']:v['value_rows'] for v in pub['validation']['references']}
            if actual!=expected or sum(actual.values())!=pub['row_count']:raise ValueError('Live row count mismatch')
            db_rows[dataset]=sum(actual.values());definitions.update(pub['definitions'])
            summaries.update({v['reference_id']:v for v in pub['validation']['references']})
            if dataset not in paths:paths[dataset]=OLD/'collection-cache'/(dataset+'.parquet')
            print(dict(live_verified=dataset,references=len(actual),rows=sum(actual.values())),flush=True)
    if len(definitions)!=progress['total_loaded']:raise ValueError('Global distinct count mismatch')
    # Every old definition remains byte-semantically unchanged.
    old_catalog=base.load_catalog(ROOT/original['catalog_path'])
    for d in old_catalog:
        if d['id'] in old_ids and d!=definitions[d['id']]:raise ValueError('Old definition changed')
    formulas=[fingerprint(d['formula']) for d in definitions.values()]
    if len(set(formulas))!=len(formulas):raise ValueError('Lexical formula duplicate')
    cache=output/'collection-cache';cache.mkdir(exist_ok=True)
    series=[]
    jobs=[(dataset,path,publications[dataset],cache) for dataset,path in paths.items()]
    # Separate bounded local validation processes; no extra database writers.
    with ProcessPoolExecutor(max_workers=3) as pool:
        cache_hashes=dict(pool.map(verify_cache_job,jobs))
    for dataset,path in paths.items():
        destination=cache/(dataset+'.parquet')
        if sha(destination)!=cache_hashes[dataset]:raise ValueError('Validated cache bytes changed')
        frame=pd.read_parquet(destination,columns=['asset_id','date','reference_id','value'])
        frame.asset_id=frame.asset_id.astype(str)
        frame.date=pd.to_datetime(frame.date)
        for ref,g in frame.groupby('reference_id'):
            s=g.set_index(['date','asset_id']).value.rename(ref)
            if s.index.has_duplicates:raise ValueError('Duplicate feature identity')
            series.append(s)
            summaries[ref].update(assets=int(g.asset_id.nunique()),months=int(g.date.nunique()),
                first_date=str(g.date.min().date()),last_date=str(g.date.max().date()))
    wide=pd.concat(series,axis=1).sort_index()
    complete=wide.notna().all(axis=1)
    first_joint=wide.index.get_level_values('date')[complete].min()
    availability=dict(asset_months=len(wide),complete_all_references_asset_months=int(complete.sum()),
        complete_all_references_first_date=None if pd.isna(first_joint) else str(first_joint.date()),
        per_reference_observed_rows={k:int(v) for k,v in wide.notna().sum().items()},imputed=False)
    save_json(output/'joint-availability.json',availability)
    # Deterministic feature-only screen; high-correlation pairs get full overlap.
    sample=wide.iloc[::max(1,len(wide)//15000)]
    corr=sample.corr(method='spearman',min_periods=1000)
    suspects=[];duplicates=[]
    for i,left in enumerate(corr):
        for right in corr.columns[i+1:]:
            rho=corr.at[left,right]
            if abs(rho)>0.98:
                pair=wide[[left,right]].dropna()
                full=float(pair.corr(method='spearman').iloc[0,1])
                item=dict(left=left,right=right,sample_spearman=float(rho),full_spearman=full,common_rows=len(pair))
                suspects.append(item)
                if abs(full)>1-1e-12:duplicates.append(item)
    if duplicates:raise ValueError('Exact monotone duplicate measurements: '+str(duplicates))
    audit=dict(status='PASSED',scope='LEXICAL_PLUS_FIXED_FEATURE_SAMPLE_WITH_FULL_OVERLAP_NEAR_MONOTONE_REVIEW',
        feature_rows=len(wide),features=len(definitions),sample_rows=len(sample),full_checked_pairs=suspects,
        exact_monotone_duplicates=duplicates,forward_labels_read=False,
        limitation='Numerical screening supports, but cannot prove semantic/statistical independence. Literature composites share inputs by design.')
    save_json(output/'duplicate-audit.json',audit)
    catalog=dict(schema_version='phenomena-reference-library-v1',reviewed_at='2026-10-03',
        purpose='Literature-bound Korean reference measurements; not approved independent alphas',
        selection_policy='Source quality, data feasibility, unique formulas and measurement validity; no future-return selection',
        definitions=[definitions[r] for r in sorted(definitions)])
    save_json(output/'catalog.json',catalog)
    program=dict(schema_version='phenomenon-program-v2',generation_id=gold.GENERATION,
        catalog_path=f'research/phenomena/reference-catalog-{len(definitions)}-20261003.json',
        catalog_sha256=sha(output/'catalog.json'),reference_datasets=list(entries.values()),legacy_gold_policy='EXCLUDED_NO_FALLBACK')
    program['program_sha256']=digest(program);save_json(output/'program.json',program)
    final=dict(progress,rows=sum(db_rows.values()),datasets=len(entries),live_database_verified=True,
        dataset_rows=db_rows,cache_file_sha256=cache_hashes,duplicate_audit_sha256=sha(output/'duplicate-audit.json'),
        candidate_program_sha256=program['program_sha256'],profitability_approved=False,pit_status='PIT_ASSUMED',
        legacy_metadata=legacy,activation_status='PREPARED_NOT_ACTIVATED')
    save_json(output/'completion.json',final)
    # Human-readable generated artifact, not an independent evidence source.
    lines=['# 레퍼런스 100개 이상 확장: 실제 적재 결과','',
        f"기존 {progress['existing']}개 + 신규 {progress['new_loaded']}개 = **{len(definitions)}개**, **{sum(db_rows.values()):,}행**, {len(entries)}개 불변 Gold 데이터셋.",
        '','모두 한국 KOSPI/KOSDAQ 보통주의 레퍼런스 측정값이다. 수익성이 확인된 독립 알파의 개수가 아니다. `PIT_ASSUMED`이며 최초 발표 빈티지의 완전한 검증은 아니다.',
        '','## 출처별 신규 적재','', '| 구분 | 요구 | 실제 신규 |','|---|---:|---:|']
    for k,n in [('academic',20),('aqr',10),('other_quant_firm',10)]:lines.append(f'| {k} | {n} | {progress["source_counts"].get(k,0)} |')
    lines += ['','한 지표는 출처 한 곳에만 집계했다. AQR/WorldQuant 이름은 한국 수익률 검증을 대신하지 않는다.',
        '','## 검증과 해석','',
        '- 원천 바이트 고정 → 가용시각/FY·단위 검증 → 서로 다른 계산기 대조 → DB 원자적 적재 → 전체 행 바이너리 해시 재조회 → 별도 커밋 후 재조회 순서.',
        '- 신규 지표는 100종목·60개 관측월 이상. 이것은 각 종목마다 5년을 보유한다는 의미가 아니다.',
        f'- 모든 {len(definitions)}개가 동시에 존재하는 종목-월은 {int(complete.sum()):,}개이며 최초는 {availability["complete_all_references_first_date"]}다. 전체 열을 일괄 완전관측 처리하면 표본이 크게 바뀐다. 가격군·재무군·장기 FY군을 가용 이력에 따라 분리하고 결측을 0으로 채우지 않는다.',
        '- 이름·부호·단조변환·기간만 바꾼 항목은 추가하지 않았다. 전 지표 수식 대조와 결정론적 측정값 표본의 순위상관 검사, 의심 쌍의 전체 교집합 검사를 수행했다.',
        '- 비가격 규모 4종은 매출·자산·자본·설비 규모라는 다른 통제 측정이다. AQR 수익성 종합은 기존 6구성요소를 문헌의 고정 방식으로 요약하므로 독립 정보 6개를 새로 얻었다는 뜻이 아니다.',
        '- WQ 지표는 일별 원식을 한국 월말에 표본화했다. 원 논문의 단기 보유 성과를 월 리밸런싱 수익성으로 옮겨 해석하면 안 된다.',
        '- 시장 입력은 전일 시가총액 가중 보통주 가격수익률 대용이며 공식 시장 TR이 아니다. 순주식수/거래량 조정도 가격조정 계수를 이용한 대용이라는 제한을 각 정의에 보존했다.',
        '- 기존 45개 데이터셋·정의와 레거시 승인 메타데이터는 변경하지 않았다. 이 작업에서 봉인 OOS나 미래 수익률로 선별하지 않았다.',
        '', '문헌 우선순위·한국 근거·최신 평가 절차는 [방법론 보고서](../../../../docs/reference-expansion-100-methods-20261003.md)를 참고한다.',
        '', '## 전체 적재 목록', '', '| ID / 한국어 이름 | 범주 | 구간 / 관측월 / 종목 | 값 행 | 출처 |','|---|---|---|---:|---|']
    for ref,d in sorted(definitions.items()):
        s=summaries[ref];sources='; '.join(f'[{v["title"]}]({v["url"]})' for v in d['sources'])
        coverage=f"{s.get('first_date','')}~{s.get('last_date','')} / {s.get('months','')}월 / {s.get('assets','')}종목"
        lines.append(f"| `{ref}`<br>{d['name_ko']} | {d['family']} | {coverage} | {s['value_rows']:,} | {sources} |")
    lines += ['','## 신규 정의의 원문 대비 차이','']
    for ref,d in sorted(definitions.items()):
        if ref not in old_ids:lines.extend([f"### {d['name_ko']} — `{ref}`",'',d['adaptation'],''])
    lines += ['## 발행에서 제외한 계산 후보','',
        'WorldQuant #3, #15, #18, #22, #34, #44, #55는 전체 실데이터의 독립 계산 대조에서 수치/순위 차이가 있어 격리했다. 임계값을 완화하거나 일치한 행만 골라 개수를 채우지 않았다. 수정된 EDGE는 가격조정계수 변화 월을 제외한 최종 정의만 적재했다.',
        '', '## 재현 경로','',
        '`scripts.capture_reference_daily` → `scripts.prepare_reference_diversity` / `scripts.build_reference_formulaic` / `scripts.build_reference_risk_diversity` → 발행 → `scripts.audit_reference_expansion_100` 순서다.',
        '이번 동결 위험 지표 배치는 EDGE 사전 보완을 별도 `scripts.prepare_edge_action_filter`로 재검증했다. 과거 `risk-build` 발행 재개에는 `--exclude-reference kr_edge_spread_reference_v1`을 사용하고, EDGE는 `edge-action-filter`의 publication만 사용한다. 새 원천으로 전체 재계산할 때에는 최신 위험 빌더에 같은 제외 규칙이 내장되어 있다.',
        '', '이 보고서의 DB 검증은 후보 활성화 직전이다. 실제 활성화와 소비 경로 확인은 별도 `activation-verification.json`으로 증명한다.']
    (output/'report.md').write_text('\n'.join(lines)+'\n')
    print(final,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    run(p.parse_args().output)
