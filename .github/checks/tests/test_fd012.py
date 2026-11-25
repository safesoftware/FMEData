"""FD012: a folder-dataset zip (Data/Parks.zip beside the folder Data/Parks) keeps up with its folder."""

import subprocess
from pathlib import Path

from fmedata_checks.checks_fd import fd012_changes, fd012_history, folder_zips
from fmedata_checks.gitdiff import Change
from fmedata_checks.tree import RepoTree

TREE = RepoTree.from_paths(["Data/Parks/Parks.shp", "Data/Parks.zip", "Data/Other.zip",
                            "Data/A/A.gdb/t.gdbtable", "Data/A/A.gdb.zip"])


def test_folder_zips_pairs_zip_with_same_named_folder():
    assert folder_zips(TREE) == {"Data/Parks.zip": "Data/Parks", "Data/A/A.gdb.zip": "Data/A/A.gdb"}


def test_pr_changing_folder_without_zip_warns():
    found = fd012_changes([Change("M", "Data/Parks/Parks.shp", None)], TREE)
    assert [(f.check_id, f.path, f.severity) for f in found] == [("FD012", "Data/Parks.zip", "warning")]
    assert "Data/Parks/" in found[0].message


def test_pr_changing_folder_and_zip_is_fine():
    assert fd012_changes([Change("M", "Data/Parks/Parks.shp", None), Change("M", "Data/Parks.zip", None)], TREE) == []


def test_pr_unrelated_change_is_fine():
    assert fd012_changes([Change("M", "Data/Other.zip", None)], TREE) == []


def git(repo: Path, *args: str, date: str | None = None) -> None:
    env = None
    if date:
        import os
        env = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def test_history_flags_zip_and_folder_changed_on_parallel_branches(tmp_path: Path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "Data" / "Parks").mkdir(parents=True)
    (tmp_path / "Data" / "Parks" / "a.shp").write_text("1", encoding="utf-8")
    (tmp_path / "Data" / "Parks.zip").write_text("z1", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "switch", "-q", "-c", "rezip")
    (tmp_path / "Data" / "Parks.zip").write_text("z2", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "rezip from the old folder")
    git(tmp_path, "switch", "-q", "main")
    (tmp_path / "Data" / "Parks" / "a.shp").write_text("2", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "edit folder")
    git(tmp_path, "merge", "-q", "--no-ff", "-m", "merge rezip", "rezip")
    assert [f.path for f in fd012_history(tmp_path, RepoTree.from_git(tmp_path))] == ["Data/Parks.zip"]


def test_history_flags_folder_changed_after_zip(tmp_path: Path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "Data" / "Parks").mkdir(parents=True)
    (tmp_path / "Data" / "Parks" / "Parks.shp").write_text("1", encoding="utf-8")
    (tmp_path / "Data" / "Parks.zip").write_text("z", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "both", date="2023-07-14T12:00:00")
    (tmp_path / "Data" / "Parks" / "Parks.shp").write_text("2", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "folder only", date="2023-07-18T12:00:00")
    found = fd012_history(tmp_path, RepoTree.from_git(tmp_path))
    assert [(f.path, f.severity) for f in found] == [("Data/Parks.zip", "warning")]
    assert "2023-07-18" in found[0].message and "2023-07-14" in found[0].message and "include" in found[0].message
