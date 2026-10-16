"""Verified discovery snapshots -> scoped graph sources; never invent clocks.

The generic bridge only accepts already normalized research rows. A provider
normalization adapter must preserve original release/version evidence upstream;
this module never substitutes an observation date for its publication date.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from engine import research_data_sources as discovery
from engine.phenomenon_research import GraphStore, TIME_FIELDS, digest


def _rows(loaded, *, scope, field_roles):
    rows=loaded['rows']
    required={'row_id',*TIME_FIELDS,*field_roles}
    if not rows or any(not required.issubset(row) for row in rows):
        raise ValueError('Normalized research rows need explicit feature, decision, outcome and observation clocks')
    req=loaded['requirement']
    # No implicit scope expansion or filtering. A narrower study needs its own
    # explicit requirement/version; import the entire validated payload.
    start=datetime.fromisoformat(scope['start']); end=datetime.fromisoformat(scope['end'])
    if not start.tzinfo or not end.tzinfo or start>end:
        raise ValueError('Timezone-aware ordered scope required')
    if str(start.date())!=req['start_date'] or str(end.date())!=req['end_date']:
        raise ValueError('Discovery and graph scope dates differ')
    if scope['universe']!=req['market']:
        raise ValueError('Discovery and graph universe differs')
    if not set(field_roles).issubset(req['variables']):
        raise ValueError('Graph fields were not in the reviewed data requirement')
    return [{key:row[key] for key in sorted(required)} for row in rows]


def import_discovery_snapshot(graph:GraphStore,case_dir,snapshot_id,*,scope,field_roles,
                              origin,stage,actor,known_at):
    loaded=discovery.load_snapshot(case_dir,snapshot_id)
    rows=_rows(loaded,scope=scope,field_roles=field_roles)
    snapshot=loaded['snapshot']
    imported_at=datetime.fromisoformat(known_at)
    if imported_at.tzinfo is None or imported_at<datetime.fromisoformat(snapshot['validated_at']):
        raise ValueError('Research import cannot predate source validation')
    if origin not in {'OBSERVED','SYNTHETIC'}:
        raise ValueError('Explicit data origin required')
    if origin=='SYNTHETIC' and not scope['universe'].startswith('SYNTHETIC'):
        raise ValueError('Synthetic scope must remain visibly synthetic')
    if scope['universe'].startswith('SYNTHETIC') and origin!='SYNTHETIC':
        raise ValueError('Synthetic scope cannot be relabeled observed')
    binding=dict(case_dir=str(Path(case_dir).absolute()),snapshot_id=snapshot_id,
                 raw_rows_sha256=digest(loaded['rows']),rows_sha256=digest(rows),origin=origin,
                 scope=scope,field_roles=field_roles,stage=stage,projection=sorted(rows[0]))
    source=graph.append_node('source',dict(
        source_ref=snapshot['source_url'],data_version=snapshot_id,rows_sha256=digest(rows),
        data_root_ids=[snapshot['artifact_sha256']],columns=sorted(rows[0]),field_roles=field_roles,
        scope=scope,stage=stage,origin=origin,pit_policy={'verified':'VERIFIED','assumed':'PIT_ASSUMED'}[snapshot['pit_status']],
        readiness='READY',discovery_binding=binding),actor=actor,role='curator',known_at=known_at)
    return {'source':source,'rows':rows}


def assert_source_bindings(graph:GraphStore):
    """Recheck upstream permission/hashes on each downstream use, not only import.

    A revoked review blocks execution even before a curator appends a graph
    invalidation event. Explicit invalidation then records the reason/history.
    Sources imported by other trusted adapters need their own validation gate.
    """
    validation=graph.validate(); checked=[]
    for record in graph.records():
        if record.get('kind')!='source' or validation['statuses'].get(record['id']) in {'INVALIDATED','SUPERSEDED'}:
            continue
        p=record['payload'];b=p.get('discovery_binding')
        if not b:continue
        loaded=discovery.load_snapshot(b['case_dir'],b['snapshot_id'])
        rows=_rows(loaded,scope=b['scope'],field_roles=b['field_roles'])
        if (digest(rows)!=p['rows_sha256'] or digest(rows)!=b['rows_sha256']
            or digest(loaded['rows'])!=b['raw_rows_sha256'] or b['projection']!=sorted(rows[0])
            or p['data_version']!=b['snapshot_id'] or p['origin']!=b['origin']
            or p['scope']!=b['scope'] or p['field_roles']!=b['field_roles'] or p['stage']!=b['stage']
            or p['pit_policy']!={'verified':'VERIFIED','assumed':'PIT_ASSUMED'}[loaded['snapshot']['pit_status']]
            or p['readiness']!='READY' or p['columns']!=sorted(rows[0])
            or p['source_ref']!=loaded['snapshot']['source_url']
            or (p['scope']['universe'].startswith('SYNTHETIC') and p['origin']!='SYNTHETIC')
            or p['data_root_ids']!=[loaded['snapshot']['artifact_sha256']]):
            raise ValueError('Discovery source binding differs from graph source')
        checked.append(record['id'])
    return checked


def load_source_rows(graph:GraphStore,source_id):
    source=graph.get(source_id)
    if source['kind']!='source' or 'discovery_binding' not in source['payload']:
        raise ValueError('Source requires an explicit trusted adapter; no legacy/raw fallback')
    assert_source_bindings(graph)
    b=source['payload']['discovery_binding']
    loaded=discovery.load_snapshot(b['case_dir'],b['snapshot_id'])
    return _rows(loaded,scope=b['scope'],field_roles=b['field_roles'])
