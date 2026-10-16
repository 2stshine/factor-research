"""Host-agent broker for bounded, evidence-linked phenomenon research.

The host agent chooses questions, explanations and follow-up experiments. This
CLI validates actions and executes registered operators; it is not an LLM or an
autonomous scheduler. Files and web content are data, never executable prompts.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

from engine.phenomenon_research import GraphStore
from engine.phenomenon_inputs import import_discovery_snapshot,assert_source_bindings,load_source_rows


def read(path):
    path=Path(path)
    if path.stat().st_size>20_000_000:raise ValueError('Action JSON exceeds 20MB')
    return json.loads(path.read_bytes())


def act(graph,action):
    """Checked action dispatcher; no arbitrary Python/SQL execution."""
    action=dict(action)
    command=action.pop('command');now=action.pop('known_at',datetime.now(timezone.utc).isoformat())
    if command=='append':
        return graph.append_node(known_at=now,**action)
    if command=='edge':return graph.append_edge(known_at=now,**action)
    if command=='study':return graph.register_study(known_at=now,**action)
    if command=='choose':return graph.choose_next_test(known_at=now,**action)
    if command=='execute':
        assert_source_bindings(graph)
        plan=graph.get(action['plan_id']);rows=load_source_rows(graph,plan['payload']['source_id'])
        result=graph.execute_test(rows=rows,known_at=now,**action)
        assert_source_bindings(graph)
        return result
    if command=='import-source':return import_discovery_snapshot(graph,known_at=now,**action)
    if command=='review':
        assert_source_bindings(graph)
        return graph.review_claim(known_at=now,**action)
    if command=='snapshot':
        assert_source_bindings(graph)
        return graph.snapshot(as_of=now,**action)
    if command=='search':
        assert_source_bindings(graph)
        return graph.search_claims(as_of=now,**action)
    if command=='strategy':
        assert_source_bindings(graph)
        return graph.create_strategy(known_at=now,**action)
    if command=='invalidate':return graph.invalidate(known_at=now,**action)
    if command=='supersede':return graph.supersede(known_at=now,**action)
    if command=='stop':return graph.stop_study(known_at=now,**action)
    if command=='register-execution':
        from engine.phenomenon_runtime import register_execution
        return register_execution(graph,registered_at=now,**action)
    if command=='execute-strategy':
        from engine.phenomenon_runtime import execute_registered
        return execute_registered(graph,**action)
    raise ValueError('Unsupported action; no unregistered code execution')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path,help='Dedicated graph directory, never legacy memory')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init').add_argument('--actors',required=True,type=Path)
    sub.add_parser('act').add_argument('--input',required=True,type=Path)
    sub.add_parser('validate')
    sub.add_parser('packet').add_argument('--study-id',required=True)
    search=sub.add_parser('search')
    search.add_argument('--query',default='');search.add_argument('--as-of')
    search.add_argument('--universe');search.add_argument('--limit',type=int,default=10)
    search.add_argument('--include-synthetic',action='store_true')
    args=parser.parse_args(argv)
    graph=GraphStore(args.root,actors=read(args.actors) if args.command=='init' else None)
    if args.command in {'init','validate'}:result=graph.validate()
    elif args.command=='packet':result=graph.packet(args.study_id)
    elif args.command=='search':
        assert_source_bindings(graph)
        result=graph.search_claims(args.query,as_of=args.as_of or datetime.now(timezone.utc).isoformat(),
                                  universe=args.universe,limit=args.limit,include_synthetic=args.include_synthetic)
    else:result=act(graph,read(args.input))
    # Imported rows stay in their immutable artifact; never accidentally dump
    # a large source or future outcomes into the host packet.
    if isinstance(result,dict) and 'rows' in result:
        result={k:v for k,v in result.items() if k!='rows'}
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False,default=str))


if __name__=='__main__':main()
