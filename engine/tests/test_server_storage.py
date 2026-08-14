from pathlib import Path

import pytest

from paperflow.server import storage


def test_project_path_never_escapes_storage_root(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path.resolve())
    project = storage.project_path("paper-123")
    assert project == tmp_path / "paper-123"
    with pytest.raises(ValueError):
        storage.project_path("../escape")
    with pytest.raises(ValueError):
        storage.resolve_project(project_dir="/tmp/outside", must_exist=False)


def test_workflow_updates_are_persistent(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    state = storage.update_workflow(project, stage="questioning", graph_revision=2)
    assert state["confirmed_graph_revision"] is None
    assert storage.read_workflow(project)["graph_revision"] == 2
    storage.update_workflow(project, confirmed_graph_revision=2)
    state = storage.invalidate_graph_confirmation(project, stage="sources_ready")
    assert state["stage"] == "sources_ready"
    assert state["confirmed_graph_revision"] is None
