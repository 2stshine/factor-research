"""Frozen strategy replay: dated Korean costs, slippage grid and attribution."""
import argparse
from html import escape
from pathlib import Path

import numpy as np

from engine import reference_snapshot_strategy as s
from engine import reference_snapshot_turnover as t
from engine import snapshot_cost_diagnostics as d
from engine.research_generation import digest, _immutable
from scripts.replay_reference_snapshot_costs import load_parent, compare
from scripts.report_reference_snapshot import MODEL_NAMES, PORTFOLIO_NAMES, metrics

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "research/phenomena/korean-equity-cost-schedule-20261016.json"
FOCUS = "selected_pca_ridge/q20_equal"


def table(headers, rows):
    return '<table><thead><tr>' + ''.join('<th>' + escape(str(x)) + '</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + escape(str(x)) + '</td>' for x in row) + '</tr>' for row in rows) + '</tbody></table>'


def report(output, result):
    pct = lambda x: f"{100 * x:,.2f}%"
    bp = lambda x: f"{10000 * x:,.2f}bp"
    parts = ['<h1>거래세·슬리피지 재계산과 KOSPI 대비 진단</h1>',
             '<p>2017-01~2026-08 월말 신호, 2017-02~2026-09 수익 116개월. 동일 스냅샷·선택 종목·비중. 재학습·갱신·실거래 없음.</p>',
             '<div class="warn">실제 공개 수수료를 참고한 시나리오이지 사용자 계좌의 실현 비용이 아닙니다. 매수·매도 수수료 각 0.015%를 전 기간에 가정하고, 매도 거래세만 당시 체결일별로 적용했습니다. 슬리피지 0·5·10·25bp는 각 매수/매도 금액에 붙는 가정으로, 측정된 시장충격이 아닙니다. 월말 가격수익이며 배당 포함 TR·월초 실제 체결이 아닙니다. 결측 0%/-100% 경로는 확정 성과나 신뢰구간이 아닙니다.</div>']
    benchmark = result['benchmark_summary']
    parts.append('<h2>공식 가격지수 기준선</h2>' + table(['지수', '연복리', '누적', '월말 최대낙폭'], [[k, pct(v['annualized_return']), pct(v['cumulative_return']), pct(v['maximum_drawdown'])] for k, v in benchmark.items()]))
    for assumption, label in zip(t.ASSUMPTIONS, ['결측 0% 가정', '결측 -100% 가정']):
        rows = []
        for key in result['scenarios']['0']['paths']:
            model, variant = key.split('/')
            vals = [result['scenarios'][str(slip)]['paths'][key]['scenarios'][assumption]['summary'] for slip in result['slippage_bps_each_side']]
            rows.append([MODEL_NAMES[model], PORTFOLIO_NAMES[variant], pct(vals[0]['annualized_gross_return'])] + [pct(v['annualized_net_return']) for v in vals])
        parts.append('<h2>' + label + '</h2>' + table(['모델', '구성', '비용 전', '슬립 0bp', '슬립 5bp', '슬립 10bp', '슬립 25bp'], rows))
    names = {'market_allocation': '시장 비중(KOSDAQ 등)', 'index_proxy_residual': '공식지수↔보유 패널 차이', 'size_allocation_within_market': '시장 내 규모 비중', 'stock_selection_within_market_size': '같은 시장·규모 내 종목 구성', 'commission_drag': '수수료', 'tax_drag': '거래세', 'slippage_drag': '슬리피지'}
    focus = result['attribution'][FOCUS][t.ASSUMPTIONS[0]]
    parts.append('<h2>대표 진단: 선택+PCA·20% 동일가중, 슬리피지 0bp</h2><p>이전 대화에서 설명한 조합을 고정해 상세 표시했습니다. 최고 성과를 다시 골라 승인한 것이 아닙니다. 다른 11개 조합과 결측 가정별 분석도 attribution.json에 보존했습니다.</p>')
    for period, values in focus['periods'].items():
        parts.append('<h3>' + period + '</h3>' + table(['원인 분류', '월평균 기여', '복리 연결 누적 격차 기여(pp)'], [[names[n], bp(v), f"{100 * values['linked_effects'][n]:+.2f}"] for n, v in values['mean_monthly_effects'].items()]))
        parts.append(f"<p>합계 누적 격차: {100 * values['terminal_wealth_gap']:+.2f}pp. 전략 누적 {pct(values['strategy']['cumulative_return'])}, KOSPI 누적 {pct(values['kospi']['cumulative_return'])}.</p>")
    parts.append('<p>시장 → 시장 내 규모 → 같은 규모 내 종목 구성 순서의 회계적 분해입니다. 규모는 당시 시총 1조원 이상/3천억원~1조원/3천억원 미만의 자체 구분입니다. 공식 KRX 규모지수 소속이 아닙니다. 시장·규모는 서로 독립적인 원인이 아니며 분해 순서에 의존합니다. 공식지수와 패널 시총가중 수익률 차이는 잔차로 남겨 종목선택 능력으로 돌리지 않았습니다. 누적 기여는 초기 자산 대비 차이를 정확히 연결한 값이며 CAGR 차이와 다릅니다.</p>')
    context = result['benchmarks']['industry_and_size_index_context']
    rows = []
    for name in list(d.SECTORS) + ['코스피 대형주', '코스피 중형주', '코스피 소형주']:
        row = [name]
        for period in ['2025', '2026_YTD']:
            found = next((v for v in context if v['period'] == period and v['index_name'] == name), None)
            row.append(pct(found['return']) if found else '미확보')
        rows.append(row)
    parts.append('<h2>업종·규모 지수 환경 — 전략 업종 기여도는 아님</h2>' + table(['KRX 지수', '2025년', '2026년 1~9월'], rows))
    parts.append('<div class="warn">종목별 과거 업종 분류·효력일과 KOSPI 구성종목별 업종 비중을 확보하지 못했습니다. 따라서 “전략이 특정 업종 때문에 몇 %p 뒤처졌다”는 결론은 아직 낼 수 없습니다. 현재 회사 프로필을 과거로 소급하지 않았습니다. 위 표는 보관된 공식 업종지수의 환경 설명이며 서로 겹치는 업종/하위 업종을 합산하지 않습니다.</div>')
    parts.append('<h2>비용 출처</h2><ul>' + ''.join('<li><a href="' + escape(url, quote=True) + '">' + escape(url) + '</a></li>' for url in result['sources']) + '</ul>')
    parts.append('<p>결과: result.json · 월별 비용 원장: slippage-*.json · 시장/규모 분해: attribution.json · 입력/코드 해시: plan.json. 원본 전략 및 이전 보고서는 변경하지 않았습니다.</p>')
    html = '<!doctype html><html lang="ko"><meta charset="utf-8"><title>비용 및 시장·규모·업종 진단</title><style>body{font:16px/1.7 system-ui;max-width:1320px;margin:32px auto;padding:20px;color:#17212b;background:#f7f9fc}table{border-collapse:collapse;width:100%;font-size:14px;background:white}td,th{padding:9px;border-bottom:1px solid #dde3eb;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#e8eef7}.warn{padding:16px;background:#fff0cb}h1,h2,h3{line-height:1.4}a{overflow-wrap:anywhere}</style>' + ''.join(parts) + '</html>'
    _immutable(output / 'report.html', html.encode())


def run(args):
    output = Path(args.output)
    panel, manifest, _ = s.load_snapshot(args.snapshot)
    parent, folds, checkpoints = load_parent(args.run, manifest)
    config = s.read_json(CONFIG)
    benchmark = d.collect_benchmarks(args.index_root, parent['signal_months'])
    # Declared, fixed diagnostics; no threshold/model search based on performance.
    plan = {'schema': 'snapshot-dated-cost-diagnostics-v1', 'parent_run': str(Path(args.run).resolve()), 'parent_plan_sha256': digest(parent),
            'parent_result_sha256': s.file_hash(Path(args.run) / 'result.json'), 'checkpoint_file_sha256': checkpoints,
            'snapshot_sha256': manifest['snapshot_sha256'], 'cost_config': config, 'cost_config_sha256': s.file_hash(CONFIG),
            'benchmark_files': benchmark['source_files'], 'signal_months': parent['signal_months'],
            'code_sha256': {name: s.file_hash(path) for name, path in [('runner', __file__), ('accounting', t.__file__), ('diagnostics', d.__file__), ('cost_kernel', t._post_cost_nav.__code__.co_filename)]},
            'diagnostic_focus': FOCUS, 'size_thresholds_KRW': [300000000000, 1000000000000],
            'attribution': 'HIERARCHICAL_MARKET_SIZE_SELECTION_PLUS_EXPLICIT_INDEX_PROXY_GAP_AND_COSTS',
            'industry_attribution': 'NO_HISTORICAL_MEMBERSHIP_INPUT',
            'refresh_performed': False, 'model_refitted': False, 'targets_changed': False,
            'empirical_use': 'HISTORICAL_REUSE_NOT_NEW_OOS'}
    s.write_json(output / 'plan.json', plan)
    s.write_json(output / 'benchmarks.json', benchmark)
    print({'status': 'PLAN_FROZEN', 'months': len(folds), 'slippage_grid': config['slippage_bps_each_side']}, flush=True)
    results = {}
    for slip in config['slippage_bps_each_side']:
        file = output / f'slippage-{slip}.json'
        if file.exists():
            result = s.read_json(file)
            if result['plan_sha256'] != digest(plan) or result['content_sha256'] != digest({k:v for k,v in result.items() if k != 'content_sha256'}):
                raise ValueError('Scenario checkpoint integrity mismatch')
        else:
            commission = config['commission_bps_each_side']
            rates = {m: (commission + slip, commission + slip + d.tax_bps(benchmark['sessions'][m], config)) for m in parent['signal_months']}
            result = t.evaluate(panel, folds, buy_bps=commission + slip, sell_bps=commission + slip, rates_by_month=rates)
            for path in [p for item in result['paths'].values() for p in item.get('scenarios', {}).values()] + list(result['baseline'].values()):
                d.components(path, config, slip, benchmark['sessions'])
            _, error = compare(folds, result)
            for key, item in result['paths'].items():
                model, variant = key.split('/')
                for assumption, path in item['scenarios'].items():
                    for fold, row in zip(folds, path['monthly']):
                        old = next(p for p in fold['models'][model]['portfolios'] if p['portfolio'] == variant)
                        expected = old['sensitivity_net_returns_not_observed'][assumption]
                        if abs((1 + row['gross_return']) * (1 - parent['round_trip_cost_scenario_bps'] / 10000) - 1 - expected) > 1e-12:
                            raise ValueError('Source gross returns changed')
            result.update(plan_sha256=digest(plan), cost_config=config, slippage_bps_each_side=slip,
                          audit={'same_gross_outcomes': True, 'max_return_reconciliation_error': error},
                          limitations=['Historical reuse; missing-return assumptions and price-disposal uncertainty remain.',
                                       'Published commission is a scenario, not a verified account/history rate. Dated sell-tax schedule from broker notices.',
                                       'Slippage is hypothetical per traded notional. No actual fills or market-impact calibration.',
                                       'Month-end price returns, not next-open fills or dividend-inclusive TR. No terminal liquidation.'])
            result['content_sha256'] = digest(result)
            s.write_json(file, result)
        results[str(slip)] = result
        print({'status': 'COST_SCENARIO_COMPLETE', 'slippage_bps_each_side': slip, 'combinations': len(result['paths'])}, flush=True)
    attribution = {}
    for key, item in results['0']['paths'].items():
        attribution[key] = {a: d.attribute(panel, folds, key, path, benchmark['returns'], a) for a, path in item['scenarios'].items()}
        print({'status': 'ATTRIBUTION_COMPLETE', 'combination': key}, flush=True)
    s.write_json(output / 'attribution.json', {'plan_sha256': digest(plan), 'results': attribution})
    result = {'plan_sha256': digest(plan), 'slippage_bps_each_side': config['slippage_bps_each_side'],
              'benchmark_summary': {market: metrics([benchmark['returns'][m][market] for m in parent['signal_months']]) for market in ['KOSPI', 'KOSDAQ']},
              'sources': sorted({config['commission_source']} | {r['source'] for r in config['tax_schedule']}),
              'scenarios': results, 'benchmarks': benchmark, 'attribution': attribution,
              'industry_status': 'INDEX_CONTEXT_ONLY_ASSET_INDUSTRY_ATTRIBUTION_UNAVAILABLE', 'alpha_approved': False,
              'data_requirements': [{'id': 'HISTORICAL_ASSET_SECTOR', 'status': 'MISSING',
                 'needed': 'asset_id, taxonomy, sector, effective_from/to, historical available_at and provenance; official benchmark sector constituent weights',
                 'internal_evidence': 'Frozen price panel has no sector. DATA_INVENTORY.md reports FMP/DART current profiles without historical effective dates. Local stock krxapi SECT_TP_NM and marcap Dept are market-board divisions, not industry.',
                 'public_search': ['KRX 업종분류 현황 과거 일자 업종분류 종목', 'site.data.krx.co.kr 업종분류'],
                 'public_sources': ['https://index.krx.co.kr/main/main.jsp', 'https://kind.krx.co.kr/valueup/invstindicstocks.do?method=valueupInvstIndicRankIsuMain'],
                 'outcome': 'Industry classification services identified, no time-valid asset-level history obtained in this offline run. No current-profile backfill.'}]}
    # Avoid copying bulky monthly arrays into the summary file.
    compact = {k:v for k,v in result.items() if k not in {'scenarios','attribution','benchmarks'}}
    compact['scenario_files'] = {str(slip): {'file': f'slippage-{slip}.json', 'sha256': s.file_hash(output / f'slippage-{slip}.json')} for slip in config['slippage_bps_each_side']}
    compact['attribution_file_sha256'] = s.file_hash(output / 'attribution.json')
    compact['benchmarks_file_sha256'] = s.file_hash(output / 'benchmarks.json')
    compact['summary'] = {str(slip): {key: {a:p['summary'] for a,p in v['scenarios'].items()} for key,v in result['paths'].items()} for slip,result in results.items()}
    s.write_json(output / 'result.json', compact)
    report(output, result)
    print({'status': 'COMPLETE_WITH_INDUSTRY_MEMBERSHIP_LIMITATION', 'output': str(output)}, flush=True)
    return compact


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    p.add_argument('--snapshot', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--index-root', default='/Users/mac/Documents/GitHub/TeamAlpha-data/data/index/krxapi')
    run(p.parse_args())
