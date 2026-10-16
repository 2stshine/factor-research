# -*- coding: utf-8 -*-
"""Bounded AST inspection of released frozen snippets. Never import/execute them.

This describes syntactic data dependencies, not economic meaning, PIT availability,
formula equivalence, calendar completeness, correlation motifs or runtime results.
"""
from __future__ import annotations
import ast
from collections import Counter
import hashlib
import json
import sys

VERSION = 'frozen-source-structure-v1'
PERIOD_CONSTANTS = frozenset({'LOOKBACK_MONTHS', 'WINDOW_MONTHS', 'MIN_OBSERVATIONS',
                            'SKIP_MONTHS', 'SEGMENT_MONTHS', 'SEASONAL_LAG'})
FAMILIES = {
    'ACCOUNTING_STOCK': ('current_assets', 'current_liabilities', 'retained_earnings',
        'total_equity', 'total_liabilities', 'noncurrent_assets', 'capital_stock',
        'total_assets', 'noncurrent_liabilities'),
    'ACCOUNTING_FLOW': ('revenue_ttm', 'operating_income_ttm', 'pretax_income_ttm', 'net_income_ttm'),
    'PRICE': ('adj_close',), 'TRADING': ('adv20', 'trading_value'),
    'CAPITALIZATION': ('market_cap',),
    'PRECOMPUTED_LIQUIDITY': ('amihud_illiquidity_1m',),
    'PRECOMPUTED_PRICE_RISK': ('daily_volatility_252d', 'max_daily_return_1m'),
}
FIELD_FAMILY = {field: family for family, fields in FAMILIES.items() for field in fields}
CONTROLS = {'asset_id', 'ym', 'market'}
METHODS = frozenset({'where', 'copy', 'shift', 'transform', 'groupby', 'reindex', 'notna',
    'var', 'cov', 'sqrt', 'to_numpy', 'sort_values', 'eq', 'min', 'max', 'clip', 'rolling',
    'pow', 'std', 'gt', 'reset_index', 'mean', 'astype', 'log', 'set_index'})


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def inspect_source(source, params):
    result = {'rule_version': VERSION, 'status': 'BOUNDED_STATIC_ANALYSIS', 'inputs': [],
        'operations': [], 'unknowns': [], 'declared_period_params': [],
        'calendar_month_field_in_mask': False, 'calendar_continuity_verified': False,
        'runtime_or_pit_verified': False, 'weight_roles': 'NOT_INFERRED',
        'economic_mechanism': 'NOT_INFERRED', 'correlation_or_beta_motif': 'NOT_INFERRED'}
    if not isinstance(source, str) or not source.strip():
        result.update(status='UNKNOWN', unknowns=[{'code': 'SOURCE_NOT_RECORDED'}]);return result
    if len(source) > 100_000:
        raise ValueError('Frozen snippet exceeds bounded parser size')
    try:
        tree = ast.parse(source)
    except SyntaxError:
        result.update(status='UNKNOWN', unknowns=[{'code': 'SOURCE_PARSE_ERROR'}]);return result
    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(tree.body) != 1 or len(funcs) != 1 or len(funcs[0].args.args) != 1:
        result.update(status='UNKNOWN', unknowns=[{'code': 'UNSUPPORTED_FUNCTION_SHAPE'}]);return result
    function = funcs[0]
    frame_name = function.args.args[0].arg

    def span(node):
        return {'line': node.lineno, 'column': node.col_offset, 'end_line': node.end_lineno,
                'end_column': node.end_col_offset, 'text': ast.get_source_segment(source, node)}

    # Return-dependency pruning is only valid without mutation. Check the whole
    # function, including otherwise dead assignments. Do not infer alias effects
    # or resolve dynamic flags/keyword dictionaries into an inplace guarantee.
    mutations = [arg for node in ast.walk(function) if isinstance(node, ast.Call)
                 for arg in node.keywords if arg.arg is None or
                 arg.arg == 'inplace' and not (isinstance(arg.value, ast.Constant)
                                               and arg.value.value is False)]
    if mutations:
        result.update(status='UNKNOWN', unknowns=[{'code': 'POSSIBLE_INPLACE_MUTATION',
            'source_span': span(arg.value)} for arg in mutations]);return result
    # One current case has a loop and dataframe writes. Do not silently flatten
    # control flow or mistake derived columns for raw fields.
    def simple_assignment(node):
        if len(node.targets) != 1:return False
        target = node.targets[0]
        return isinstance(target, ast.Name) or (isinstance(target, (ast.Tuple, ast.List))
            and isinstance(node.value, (ast.Tuple, ast.List)) and len(target.elts)==len(node.value.elts)
            and all(isinstance(item, ast.Name) for item in target.elts))
    if any(not isinstance(n, (ast.Assign, ast.Return)) or
           isinstance(n, ast.Assign) and not simple_assignment(n)
           for n in function.body) or sum(isinstance(n, ast.Return) for n in function.body) != 1 or not isinstance(function.body[-1], ast.Return):
        result.update(status='UNKNOWN', unknowns=[{'code': 'CONTROL_FLOW_OR_DERIVED_COLUMN_WRITE'}]);return result
    env = {}
    for statement in function.body[:-1]:
        target, prior = statement.targets[0], dict(env)
        if isinstance(target, ast.Name):env[target.id] = (statement.value, prior)
        else:
            for name, value_node in zip(target.elts, statement.value.elts):
                env[name.id] = (value_node, prior)
    root = (function.body[-1].value, dict(env))
    inputs, ops, unknown, seen, used_constants = {}, {}, {}, set(), set()
    dynamic_contexts = []  # Keep memoization identities alive for mask lambdas.

    def miss(code, node):
        unknown[(code, node.lineno, node.col_offset)] = {'code': code, 'source_span': span(node)}

    def resolve(ref):
        node, context = ref
        while isinstance(node, ast.Name) and node.id in context:
            node, context = context[node.id]
        return node, context

    def is_frame(ref):
        node, context = resolve(ref)
        if isinstance(node, ast.Name):return node.id == frame_name
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {'copy', 'sort_values', 'groupby'}
                and is_frame((node.func.value, context)))

    def value(node, context):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float, str, bool, type(None)):
            return {'status': 'LITERAL', 'value': node.value, 'expression': ast.unparse(node)}
        if isinstance(node, ast.Name) and node.id in PERIOD_CONSTANTS:
            used_constants.add(node.id)
            if node.id in context:
                return {'status':'UNKNOWN', 'expression':node.id, 'reason':'LOCAL_CONSTANT_SHADOWING'}
            key = node.id.lower()
            if key in params and type(params[key]) is int and params[key] >= 0:
                return {'status': 'EXACT_PARAM_BINDING', 'value': params[key], 'param': key, 'expression': node.id}
        return {'status': 'UNKNOWN', 'expression': ast.unparse(node)}

    def add_field(field, role, node):
        # Identifiers/dates can constrain a numeric result; they are not numeric
        # measurements simply because they occur in the return dependency graph.
        if field in CONTROLS and role in {'NUMERIC_OPERAND', 'PREDICATE_OPERAND'}:role = 'CONTROL'
        key = (field, role, node.lineno, node.col_offset)
        inputs[key] = {'field': field, 'family': FIELD_FAMILY.get(field, 'CONTROL' if field in CONTROLS else 'OTHER_UNKNOWN'),
                       'role': role, 'source_span': span(node)}

    def add_op(kind, node, role, **extra):
        ops[(kind, role, node.lineno, node.col_offset)] = {'kind': kind, 'role': role,
                                                        'source_span': span(node), **extra}

    def visit(ref, role='NUMERIC_OPERAND'):
        node, context = ref
        key = (id(node), id(context), role)
        if key in seen:return
        seen.add(key)
        if isinstance(node, ast.Name):
            if node.id in context:visit(context[node.id], role)
            elif node.id in PERIOD_CONSTANTS:used_constants.add(node.id)
            elif node.id not in {frame_name, 'np', 'pd'} and node.id not in PERIOD_CONSTANTS:
                miss('UNRESOLVED_NAME', node)
            return
        if isinstance(node, ast.Constant):return
        if isinstance(node, (ast.List, ast.Tuple)):
            for item in node.elts:visit((item, context), role)
            return
        if isinstance(node, ast.Subscript):
            if is_frame((node.value, context)):
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    add_field(node.slice.value, role, node)
                else:miss('DYNAMIC_OR_MULTI_FIELD_SELECTOR', node)
                visit((node.value, context), 'FRAME_CONTROL')
            else:miss('UNRESOLVED_SELECTOR_BASE', node)
            return
        if isinstance(node, ast.Attribute):
            if node.attr == 'index':visit((node.value, context), 'INDEX_ALIGNMENT')
            else:miss('UNSUPPORTED_ATTRIBUTE', node)
            return
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Attribute) or node.func.attr not in METHODS:
                miss('UNSUPPORTED_CALL', node);return
            method, base = node.func.attr, node.func.value
            self_role = ('MASK' if role == 'MASK' else 'PREDICATE_OPERAND') if method in {'eq', 'gt', 'notna'} else role
            kwargs = {arg.arg: value(arg.value,context) for arg in node.keywords if arg.arg}
            details = {'arguments': [value(arg,context) for arg in node.args], 'keywords': kwargs}
            if method in {'rolling', 'shift'}:
                details['period_basis'] = 'ROW_WINDOW_NOT_CALENDAR_GUARANTEE' if method == 'rolling' else 'ROW_LAG_NOT_CALENDAR_GUARANTEE'
                period = node.args[0] if node.args else next((arg.value for arg in node.keywords if arg.arg in {'window', 'periods'}), None)
                if period is not None:
                    details['period'] = value(period,context)
                    if details['period']['status'] == 'UNKNOWN':miss('UNRESOLVED_PERIOD', period)
            if method not in {'copy', 'reindex', 'reset_index'}:add_op(method, node, role, **details)
            if method in {'log', 'sqrt'} and isinstance(base, ast.Name) and base.id == 'np':pass
            else:visit((base, context), self_role)
            for index, arg in enumerate(node.args):
                arg_role = ('MASK' if method == 'where' and index == 0 else
                            'GROUP_KEY' if method == 'groupby' else
                            'SORT_KEY' if method == 'sort_values' else
                            'INDEX_ALIGNMENT' if method in {'reindex','reset_index'} else self_role)
                if method in {'groupby', 'sort_values'} and is_frame((base, context)):
                    literals = arg.elts if isinstance(arg, (ast.List, ast.Tuple)) else [arg]
                    for literal in literals:
                        if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                            add_field(literal.value, arg_role, literal)
                        else:visit((literal, context), arg_role)
                elif method == 'transform' and not isinstance(arg, ast.Constant):
                    miss('TRANSFORM_BODY_NOT_TRACED',arg)
                elif method == 'where' and index == 0 and isinstance(arg, ast.Lambda):
                    if len(arg.args.args)==1 and not arg.args.defaults and not arg.args.kwonlyargs:
                        bound = dict(context);bound[arg.args.args[0].arg] = (base, context)
                        dynamic_contexts.append(bound)
                        visit((arg.body,bound),'MASK')
                    else:miss('UNSUPPORTED_MASK_LAMBDA',arg)
                elif method == 'shift' and index > 0:
                    miss('UNTRACED_POSITIONAL_ARGUMENT', arg)
                elif method not in {'shift','rolling','astype','transform','reset_index'}:
                    visit((arg, context), arg_role)
            for arg in node.keywords:
                if arg.arg is None:miss('DYNAMIC_KEYWORD_ARGUMENT', arg.value)
                elif method in {'groupby','sort_values'} and arg.arg in {'by','level'}:
                    miss('KEYWORD_GROUP_OR_SORT_NOT_TRACED',arg.value)
                elif method == 'rolling' and arg.arg in {'window','min_periods'}:
                    if arg.arg == 'min_periods' and kwargs[arg.arg]['status']=='UNKNOWN':
                        miss('UNRESOLVED_MIN_PERIODS',arg.value)
                    # window is checked as the period above.
                elif method == 'shift' and arg.arg == 'periods':pass  # checked above
                elif method == 'transform' and arg.arg in {'func','function'}:
                    miss('TRANSFORM_BODY_NOT_TRACED',arg.value)
                elif method == 'where' and arg.arg in {'cond','condition'}:
                    visit((arg.value,context),'MASK')
                elif ((method in {'cov','where'} and arg.arg == 'other') or
                      (method == 'clip' and arg.arg in {'lower','upper'})):
                    visit((arg.value,context),self_role)
                elif arg.arg == 'inplace':pass  # whole-function guard permits only literal False
                elif arg.arg in {'groupby': {'sort'}, 'sort_values': {'kind'},
                                  'reset_index': {'drop','level'}, 'var': {'ddof'},
                                  'std': {'ddof'}, 'cov': {'ddof'}}.get(method,set()):
                    if kwargs[arg.arg]['status'] != 'LITERAL':
                        miss('UNTRACED_KEYWORD_ARGUMENT',arg.value)
                else:miss('UNTRACED_KEYWORD_ARGUMENT',arg.value)
            return
        if isinstance(node, (ast.BinOp, ast.Compare, ast.BoolOp, ast.UnaryOp)):
            mask = isinstance(node, (ast.Compare, ast.BoolOp)) or isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitAnd, ast.BitOr))
            child_role = ('MASK' if role == 'MASK' else 'PREDICATE_OPERAND') if mask else role
            operators = [type(op).__name__ for op in node.ops] if isinstance(node,ast.Compare) else [type(node.op).__name__]
            add_op('operator', node, child_role, operators=operators)
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):visit((child, context), child_role)
            return
        miss('UNSUPPORTED_EXPRESSION', node)

    visit(root)
    result['inputs'] = sorted(inputs.values(), key=lambda row:(row['field'], row['role'], row['source_span']['line'], row['source_span']['column']))
    result['operations'] = sorted(ops.values(), key=lambda row:(row['source_span']['line'], row['source_span']['column'], row['kind'], row['role']))
    result['unknowns'] = sorted(unknown.values(), key=lambda row:(row['code'], row['source_span']['line'], row['source_span']['column']))
    result['status'] = 'PARTIAL' if unknown else 'BOUNDED_STATIC_ANALYSIS'
    result['calendar_month_field_in_mask'] = any(row['field']=='ym' and row['role']=='MASK' for row in result['inputs'])
    for name in sorted(PERIOD_CONSTANTS):
        key = name.lower()
        if key in params:
            result['declared_period_params'].append({'param':key, 'value':params[key],
                'used_constant':name in used_constants})
    return result


def project(payload):
    if payload.get('scope') != 'AUTHENTICATED_RELEASED_RECORDS_ONLY':raise ValueError('Scope required')
    records, seen = [], set()
    for row in payload['records']:
        if row['record_id'] in seen:raise ValueError('Duplicate released identity')
        seen.add(row['record_id'])
        for key in ['record_id','definition_hash','packet_sha256']:
            if not isinstance(row.get(key),str) or not row[key]:raise ValueError('Frozen identity required')
        analysis = inspect_source(row['source'], row['params'])
        records.append({key:row[key] for key in ['record_id','definition_hash','packet_sha256']} | {
            'source_sha256':hashlib.sha256(row['source'].encode()).hexdigest(),
            'params_sha256':digest(row['params']), 'analysis':analysis})
    counts=Counter(row['analysis']['status'] for row in records)
    fields=Counter();families=Counter()
    for row in records:
        numeric=[i for i in row['analysis']['inputs'] if i['role'] in {'NUMERIC_OPERAND','PREDICATE_OPERAND'}]
        fields.update({i['field'] for i in numeric});families.update({i['family'] for i in numeric})
    return {'schema_version':VERSION, 'scope':payload['scope'], 'catalog_sha256':payload['catalog_sha256'],
        'records':records, 'counts':dict(counts), 'numeric_field_record_counts':dict(sorted(fields.items())),
        'numeric_family_record_counts':dict(sorted(families.items())),
        'count_unit':'RELEASED_RECORDS_WITH_STATIC_NUMERIC_DEPENDENCY_OVERLAPPING',
        'independent_dimension_computed':False, 'performance_used':False,
        'limits':['Static source references are not observed data, PIT or execution coverage.',
                  'Control-flow/derived-column writes remain UNKNOWN in v1.',
                  'Numeric operands may include weights; weight and correlation/beta motifs are not inferred.',
                  'Row periods and presence of a month mask do not prove calendar continuity.']}


if __name__=='__main__':
    payload=json.load(sys.stdin)
    print(json.dumps(project(payload),ensure_ascii=False,separators=(',',':')))
