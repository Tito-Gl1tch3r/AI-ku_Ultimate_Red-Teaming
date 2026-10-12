from pathlib import Path

import pytest

from ai.tool_policy import build_tool_policy
from ai.workspace_manager import (
    cleanup_run_workspace,
    ensure_within_workspace,
)


def test_ensure_within_workspace_accepts_relative_candidate_paths_from_workspace_root(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    inside_path = workspace_root / "source" / "plugin.php"
    inside_path.parent.mkdir()
    inside_path.write_text("<?php\n", encoding="utf-8")

    assert ensure_within_workspace(workspace_root, inside_path) == inside_path.resolve()
    assert ensure_within_workspace(workspace_root, Path("source/plugin.php")) == inside_path.resolve()



def test_ensure_within_workspace_rejects_paths_outside_workspace(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    outside_path = tmp_path / "outside.php"
    outside_path.write_text("<?php\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside workspace"):
        ensure_within_workspace(workspace_root, outside_path)



def test_ensure_within_workspace_rejects_symlink_escape_attempts(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_path = outside_dir / "secret.php"
    outside_path.write_text("<?php\n", encoding="utf-8")

    linked_dir = workspace_root / "source" / "linked"
    linked_dir.parent.mkdir()
    linked_dir.symlink_to(outside_dir, target_is_directory=True)

    with pytest.raises(ValueError, match="outside workspace"):
        ensure_within_workspace(workspace_root, linked_dir / "secret.php")



def test_ensure_within_workspace_rejects_nonexistent_relative_paths_with_parent_escape(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    with pytest.raises(ValueError, match="outside workspace"):
        ensure_within_workspace(workspace_root, Path("../outside/missing.php"))

    with pytest.raises(ValueError, match="outside workspace"):
        ensure_within_workspace(workspace_root, Path("source/../../outside/missing.php"))


def test_build_tool_policy_returns_bridge_metadata(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    policy = build_tool_policy(workspace_root)

    assert policy == {
        "workspace_root": str(workspace_root.resolve()),
        "enforcement": "handled_by_open_multi_agent",
    }
