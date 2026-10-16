"""Explicit compare-and-swap cutover; archives pointers, imports no old alpha."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path

from engine import research_generation as generation

ID='phenomenon-research-v1'


def activate(repo_root,*,archive_manifest,expected_pointer_sha256,apply=False):
    root=generation._no_symlinks(repo_root)
    lock=generation._no_symlinks(root/'research/.generation-cutover.lock')
    lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('a+b') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        current=generation.load_active_generation(root)
        path=root/generation.ACTIVE_PATH
        raw=path.read_bytes();old=json.loads(raw)
        if old['pointer_sha256']!=expected_pointer_sha256:
            raise ValueError('Active generation changed; inspect before cutover')
        if old['generation_id']==ID:
            return dict(status='ALREADY_ACTIVE',generation_id=ID,approved_factor_count=len(current['approved_factors']))
        if current['approved_factors']:
            raise ValueError('Nonempty generation requires explicit admission migration review')
        built=generation.initialize_generation(root,archive_manifest=archive_manifest,generation_id=ID,activate=False)
        manifest=built['generation']
        pointer=dict(schema_version='active-research-generation-v1',generation_id=ID,
                     generation_sha256=manifest['generation_sha256'],
                     manifest_path=str(Path(built['manifest_path']).relative_to(root)),legacy_gold_policy='EXCLUDED_NO_FALLBACK')
        pointer['pointer_sha256']=generation.digest(pointer)
        if not apply:return dict(status='DRY_RUN',previous=old,new=pointer,approved_factor_count=0)
        history=root/'research/generations/transition-history'
        generation._immutable(history/(old['pointer_sha256']+'.json'),raw)
        receipt=dict(schema_version='research-generation-cutover-v1',previous=old,new=pointer,
                     legacy_imported=False,approved_factors_imported=0)
        generation._immutable(history/(generation.digest(receipt)+'.json'),generation.canonical(receipt)+b'\n')
        temporary=path.with_name('.active-generation-'+pointer['pointer_sha256']+'.tmp')
        generation._immutable(temporary,generation.canonical(pointer)+b'\n')
        # Re-check after all preparation; cooperating writers serialize on lock.
        if path.read_bytes()!=raw:raise ValueError('Active pointer changed during cutover')
        os.replace(temporary,path)
        observed=generation.load_active_generation(root)
        if observed['generation_id']!=ID:raise ValueError('Cutover verification failed')
        return dict(status='ACTIVE',generation_id=ID,previous_generation=old['generation_id'],
                    previous_pointer_preserved=str(history/(old['pointer_sha256']+'.json')),
                    approved_factor_count=0,legacy_imported=False)
