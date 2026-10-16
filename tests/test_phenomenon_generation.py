import json
from pathlib import Path
import pytest
from engine import research_generation as g
from engine.phenomenon_generation import activate,ID


def setup(tmp_path,monkeypatch):
    archive={'archive_id':'a'*64,'manifest_sha256':'b'*64}
    monkeypatch.setattr(g,'verify_legacy_snapshot',lambda _:archive)
    g.initialize_generation(tmp_path,archive_manifest='unused',activate=True)
    pointer=json.loads((tmp_path/g.ACTIVE_PATH).read_bytes())
    return pointer


def test_cutover_preserves_previous_and_keeps_empty_alpha(tmp_path,monkeypatch):
    p=setup(tmp_path,monkeypatch)
    result=activate(tmp_path,archive_manifest='unused',expected_pointer_sha256=p['pointer_sha256'],apply=True)
    assert result['status']=='ACTIVE'
    assert json.loads(Path(result['previous_pointer_preserved']).read_bytes())==p
    current=g.load_active_generation(tmp_path)
    assert current['generation_id']==ID and current['approved_factors']==[]
    new=json.loads((tmp_path/g.ACTIVE_PATH).read_bytes())
    assert activate(tmp_path,archive_manifest='unused',expected_pointer_sha256=new['pointer_sha256'],apply=True)['status']=='ALREADY_ACTIVE'


def test_cutover_dryrun_and_compare_swap(tmp_path,monkeypatch):
    p=setup(tmp_path,monkeypatch)
    activate(tmp_path,archive_manifest='unused',expected_pointer_sha256=p['pointer_sha256'])
    assert g.load_active_generation(tmp_path)['generation_id']==g.DEFAULT_GENERATION
    with pytest.raises(ValueError,match='changed'):
        activate(tmp_path,archive_manifest='unused',expected_pointer_sha256='c'*64,apply=True)
