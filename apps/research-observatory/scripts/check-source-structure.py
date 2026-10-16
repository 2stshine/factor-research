# -*- coding: utf-8 -*-
"""Standard-library negative and metamorphic tests; no snippet is executed."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source_structure',ROOT/'src/research-status/source_structure.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def semantic(report):
    def clean(value):
        if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k!='source_span'}
        if isinstance(value,list):return [clean(v) for v in value]
        return value
    return clean(report)

def fields(report,role=None):return {i['field'] for i in report['inputs'] if role is None or i['role']==role}

class SourceStructureTests(unittest.TestCase):
    def test_cov_other_keyword_matches_positional_dependency(self):
        prefix='def compute(frame):\n    return frame["adj_close"].rolling(3).cov('
        reports=[m.inspect_source(prefix+arg+')\n',{}) for arg in
                 ['frame["market_cap"]','other=frame["market_cap"]']]
        for r in reports:
            self.assertEqual(r['status'],'BOUNDED_STATIC_ANALYSIS')
            self.assertEqual(r['unknowns'],[])
            self.assertEqual(fields(r,'NUMERIC_OPERAND'),{'adj_close','market_cap'})
            self.assertFalse(r['runtime_or_pit_verified'])
        # Source spans and call syntax differ; numeric dependencies do not.
        self.assertEqual(fields(reports[0]),fields(reports[1]))
    def test_shift_untraced_fill_value_is_partial_for_both_call_styles(self):
        prefix='def compute(frame):\n    return frame["adj_close"].shift('
        for arg in ['1, None, 0, frame["market_cap"]',
                    'periods=1, fill_value=frame["market_cap"]']:
            with self.subTest(arg=arg):
                r=m.inspect_source(prefix+arg+')\n',{})
                self.assertEqual(r['status'],'PARTIAL')
                self.assertTrue(any('market_cap' in u['source_span']['text'] for u in r['unknowns']))
                self.assertFalse(r['calendar_continuity_verified'])
        for arg in ['1','periods=1']:
            self.assertEqual(m.inspect_source(prefix+arg+')\n',{})['status'],'BOUNDED_STATIC_ANALYSIS')
    def test_unhandled_keywords_and_dynamic_scalar_options_are_partial(self):
        for expression in ['frame["adj_close"].rolling(3, on=frame["market_cap"]).mean()',
                           'frame["adj_close"].shift(1, freq="D")',
                           'frame["adj_close"].std(ddof=frame["market_cap"])',
                           'frame["adj_close"].rolling(3).cov(other=frame["market_cap"], unsupported=True)',
                           'frame.groupby(frame["asset_id"], sort=frame["market_cap"])["adj_close"]']:
            with self.subTest(expression=expression):
                r=m.inspect_source('def compute(frame):\n    return '+expression+'\n',{})
                self.assertEqual(r['status'],'PARTIAL')
                self.assertIn('UNTRACED_KEYWORD_ARGUMENT',{u['code'] for u in r['unknowns']})
    def test_possible_inplace_in_dead_assignment_invalidates_whole_function(self):
        for arg in ['inplace=True','inplace=flag','**options','inplace=frame["market_cap"].gt(0)']:
            with self.subTest(arg=arg):
                s='def compute(frame):\n    x=frame["adj_close"].copy()\n    unused=x.where(frame["total_assets"]>0, '+arg+')\n    return x\n'
                r=m.inspect_source(s,{})
                self.assertEqual(r['status'],'UNKNOWN');self.assertEqual(r['inputs'],[])
                self.assertEqual(r['operations'],[])
                self.assertEqual(r['unknowns'][0]['code'],'POSSIBLE_INPLACE_MUTATION')
                self.assertEqual(r['unknowns'][0]['source_span']['line'],3)
                self.assertFalse(r['runtime_or_pit_verified'])
    def test_literal_false_inplace_does_not_invent_dead_mutation(self):
        s='def compute(frame):\n    x=frame["adj_close"].copy()\n    unused=x.where(frame["total_assets"]>0, inplace=False)\n    return x\n'
        r=m.inspect_source(s,{})
        self.assertEqual(r['status'],'BOUNDED_STATIC_ANALYSIS')
        self.assertEqual(fields(r),{'adj_close'})
        live=m.inspect_source(s.replace('return x','return unused'),{})
        self.assertEqual(live['status'],'BOUNDED_STATIC_ANALYSIS')
        self.assertIn('total_assets',fields(live,'MASK'))
    def test_dead_comments_and_definition_name_do_not_create_fields(self):
        a='def compute(frame):\n    x = frame["market_cap"]\n    return x\n'
        b='def renamed_factor(frame):\n    # frame["not_an_input"]\n    dead = frame["total_assets"]\n    x = frame["market_cap"]\n    return x\n'
        self.assertEqual(semantic(m.inspect_source(a,{})),semantic(m.inspect_source(b,{})))
        self.assertEqual(fields(m.inspect_source(b,{})),{'market_cap'})
    def test_return_dependency_uses_assignment_time_not_last_alias(self):
        source='def compute(frame):\n    x=frame["adj_close"]\n    saved=x\n    x=frame["total_assets"]\n    return saved\n'
        self.assertEqual(fields(m.inspect_source(source,{})),{'adj_close'})
    def test_ratio_order_and_mask_operator_preserved(self):
        a='def compute(frame):\n    return frame["revenue_ttm"] / frame["total_assets"].where(frame["total_assets"] > 0)\n'
        b=a.replace(' > 0',' != 0')
        self.assertNotEqual(semantic(m.inspect_source(a,{})),semantic(m.inspect_source(b,{})))
        div=next(o for o in m.inspect_source(a,{})['operations'] if o.get('operators')==['Div'])
        self.assertEqual(div['source_span']['text'],a.split('return ')[1].strip())
        self.assertIn('revenue_ttm',div['source_span']['text'].split('/')[0])
    def test_unknown_dynamic_selector_or_operation_never_executes(self):
        for source,code in [
            ('def compute(frame):\n    return frame[WHICH]\n','DYNAMIC_OR_MULTI_FIELD_SELECTOR'),
            ('def compute(frame):\n    return dangerous_api()\n','UNSUPPORTED_CALL')]:
            r=m.inspect_source(source,{})
            self.assertEqual(r['status'],'PARTIAL');self.assertIn(code,{u['code'] for u in r['unknowns']})
            self.assertEqual(r['inputs'],[])
    def test_derived_column_writes_and_loop_remain_unknown(self):
        r=m.inspect_source('def compute(frame):\n    frame["derived"]=frame["adj_close"]\n    return frame["derived"]\n',{})
        self.assertEqual(r['status'],'UNKNOWN');self.assertEqual(r['inputs'],[])
    def test_only_exact_allowlisted_period_params_resolve(self):
        s='def compute(frame):\n    return frame["amihud_illiquidity_1m"].rolling(WINDOW_MONTHS,min_periods=MIN_OBSERVATIONS).mean()\n'
        r=m.inspect_source(s,{'window_months':6,'min_observations':4})
        o=next(o for o in r['operations'] if o['kind']=='rolling')
        self.assertEqual(o['period']['value'],6);self.assertEqual(o['keywords']['min_periods']['value'],4)
        self.assertEqual(o['period_basis'],'ROW_WINDOW_NOT_CALENDAR_GUARANTEE')
        self.assertFalse(r['calendar_continuity_verified'])
        self.assertFalse(r['calendar_month_field_in_mask'])
        bad=m.inspect_source(s.replace('WINDOW_MONTHS','LOOKBACK_OTHER'),{'lookback_other':6})
        self.assertEqual(next(o for o in bad['operations'] if o['kind']=='rolling')['period']['status'],'UNKNOWN')
        arithmetic=m.inspect_source(s.replace('WINDOW_MONTHS','WINDOW_MONTHS-1'),{'window_months':6,'min_observations':4})
        self.assertEqual(arithmetic['status'],'PARTIAL')
    def test_group_sort_mask_and_numeric_roles_do_not_collapse(self):
        s='def compute(frame):\n    x=frame.sort_values(["asset_id","ym"])\n    v=x["adj_close"].groupby(x["asset_id"]).shift(1)\n    return v.where(x["ym"] > 1).reindex(frame.index)\n'
        r=m.inspect_source(s,{})
        self.assertEqual(fields(r,'NUMERIC_OPERAND'),{'adj_close'})
        self.assertIn('asset_id',fields(r,'GROUP_KEY'));self.assertIn('ym',fields(r,'SORT_KEY'));self.assertIn('ym',fields(r,'MASK'))
        self.assertTrue(r['calendar_month_field_in_mask']);self.assertFalse(r['calendar_continuity_verified'])
    def test_returned_comparison_is_not_only_a_mask(self):
        r=m.inspect_source('def compute(frame):\n    return frame["adj_close"].gt(0).astype(float)\n',{})
        self.assertIn('adj_close',fields(r,'PREDICATE_OPERAND'))
    def test_finite_self_subtraction_stays_in_mask(self):
        r=m.inspect_source('def compute(frame):\n    x=frame["adj_close"]\n    return x.where((x-x).eq(0))\n',{})
        ops=[o for o in r['operations'] if o.get('operators')==['Sub']]
        self.assertTrue(ops);self.assertTrue(all(o['role']=='MASK' for o in ops))
        self.assertEqual(r['economic_mechanism'],'NOT_INFERRED')
    def test_lambda_mask_and_tuple_bindings_preserve_inputs(self):
        r=m.inspect_source('def compute(frame):\n    a,b=frame["revenue_ttm"],frame["total_assets"]\n    return a / b.where(lambda x:x>0)\n',{})
        self.assertEqual(r['status'],'BOUNDED_STATIC_ANALYSIS')
        self.assertEqual(fields(r,'NUMERIC_OPERAND'),{'revenue_ttm','total_assets'})
    def test_all_current_released_sources_have_provenance_without_outcomes(self):
        catalog=json.loads((ROOT/'dist/data/research-catalog.json').read_text())
        def project(c):return m.project({'scope':'AUTHENTICATED_RELEASED_RECORDS_ONLY','catalog_sha256':'test',
            'records':[{'record_id':r['record_id'],'definition_hash':r['provenance']['definition_hash'],
                'packet_sha256':r['provenance']['packet_sha256'],'source':r['definition']['source'],'params':r['definition']['params']} for r in c['records']]})
        before=project(catalog)
        for r in catalog['records']:
            r['factor_name']='renamed';r['definition']['hypothesis']='arbitrary prose';r['performance']={'oos':999999};r['validation']['verdict']='CHANGED'
        self.assertEqual(before,project(catalog))
        self.assertEqual(len(before['records']),177)
        self.assertEqual(before['counts'],{'BOUNDED_STATIC_ANALYSIS':165,'PARTIAL':11,'UNKNOWN':1})
        self.assertEqual(before['numeric_family_record_counts']['PRICE'],31)
        self.assertFalse(before['performance_used']);self.assertFalse(before['independent_dimension_computed'])
        for r in before['records']:
            self.assertFalse(r['analysis']['runtime_or_pit_verified'])
            for item in r['analysis']['inputs']+r['analysis']['operations']:
                self.assertTrue(item['source_span']['text']);self.assertGreater(item['source_span']['line'],0)
    def test_transform_lambda_remains_partial_instead_of_silent_complete(self):
        source='def compute(frame):\n    return frame["total_assets"].groupby(frame["asset_id"]).transform(lambda x:x.rolling(WINDOW_MONTHS).std())\n'
        r=m.inspect_source(source,{'window_months':36})
        self.assertEqual(r['status'],'PARTIAL')
        self.assertIn('TRANSFORM_BODY_NOT_TRACED',{u['code'] for u in r['unknowns']})
    def test_local_constant_does_not_borrow_same_named_params_value(self):
        r=m.inspect_source('def compute(frame):\n    WINDOW_MONTHS=3\n    return frame["adj_close"].rolling(WINDOW_MONTHS).mean()\n',{'window_months':6})
        o=next(o for o in r['operations'] if o['kind']=='rolling')
        self.assertEqual(o['period']['status'],'UNKNOWN');self.assertNotIn('value',o['period'])
        self.assertEqual(r['status'],'PARTIAL')
    def test_keyword_group_and_sort_not_silently_complete(self):
        for expression in ['frame["adj_close"].groupby(by=frame["market"]).mean()',
                           'frame.sort_values(by=["asset_id","ym"])["adj_close"]']:
            r=m.inspect_source('def compute(frame):\n    return '+expression+'\n',{})
            self.assertEqual(r['status'],'PARTIAL')
            self.assertIn('KEYWORD_GROUP_OR_SORT_NOT_TRACED',{u['code'] for u in r['unknowns']})
    def test_group_demean_and_lagged_weighted_market_remain_different(self):
        a='def compute(frame):\n    x=frame["adj_close"]\n    return x-x.groupby(frame["market"]).transform("mean")\n'
        b='def compute(frame):\n    x=frame["adj_close"]\n    w=frame["market_cap"].groupby(frame["asset_id"]).shift(1)\n    return (x*w).groupby(frame["market"]).transform("sum") / w.groupby(frame["market"]).transform("sum")\n'
        ra,rb=m.inspect_source(a,{}),m.inspect_source(b,{})
        self.assertNotEqual(semantic(ra),semantic(rb));self.assertNotIn('market_cap',fields(ra));self.assertIn('market_cap',fields(rb))
        self.assertEqual(rb['weight_roles'],'NOT_INFERRED');self.assertEqual(rb['correlation_or_beta_motif'],'NOT_INFERRED')

if __name__=='__main__':unittest.main()
