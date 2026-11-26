"""KNOW-2848: FD011 is enforced, so a pull request that adds a misspelled complete workspace fails."""

import subprocess
from pathlib import Path

from fmedata_checks.__main__ import DEFAULT_CONFIG, main
from fmedata_checks.model import load_config


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "commit.gpgsign", "false")
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "branch", "base")
    return repo


def add(repo: Path, rel: str) -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text("DEFAULT_MACRO S 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", f"add {rel}")


def run_pr(repo: Path, capsys) -> tuple[int, str]:
    # The shipped checks.toml, so the test proves what CI enforces.
    code = main(["pr", "--repo", str(repo), "--base", "base", "--index", "none", "--config", str(DEFAULT_CONFIG)])
    return code, capsys.readouterr().out


def test_shipped_config_enforces_fd011():
    assert "FD011" in load_config(DEFAULT_CONFIG).enforce


def test_pr_adding_misspelled_complete_name_fails(tmp_path: Path, capsys):
    repo = make_repo(tmp_path, {"Workspaces/X/a.fmw": "DEFAULT_MACRO S 1\n"})
    add(repo, "Workspaces/X/a_Completed.fmw")
    code, out = run_pr(repo, capsys)
    assert code == 1
    assert "::error file=Workspaces/X/a_Completed.fmw::FD011 rename to Workspaces/X/a-complete.fmw" in out


def test_pr_renaming_to_misspelled_complete_name_fails(tmp_path: Path, capsys):
    repo = make_repo(tmp_path, {"Workspaces/X/a-complete.fmw": "DEFAULT_MACRO S 1\n" * 20})
    git(repo, "mv", "Workspaces/X/a-complete.fmw", "Workspaces/X/a--complete.fmw")
    git(repo, "commit", "-q", "-m", "rename")
    code, out = run_pr(repo, capsys)
    assert code == 1
    assert "::error file=Workspaces/X/a--complete.fmw::FD011" in out


def test_pr_renaming_to_complete_passes(tmp_path: Path, capsys):
    repo = make_repo(tmp_path, {"Workspaces/X/a_Completed.fmw": "DEFAULT_MACRO S 1\n" * 20})
    git(repo, "mv", "Workspaces/X/a_Completed.fmw", "Workspaces/X/a-complete.fmw")
    git(repo, "commit", "-q", "-m", "rename")
    code, out = run_pr(repo, capsys)
    assert code == 0 and "FD011" not in out


def test_pr_editing_an_existing_misspelled_name_passes(tmp_path: Path, capsys):
    repo = make_repo(tmp_path, {"Workspaces/X/a_Complete.fmw": "DEFAULT_MACRO S 1\n"})
    (repo / "Workspaces/X/a_Complete.fmw").write_text("DEFAULT_MACRO S 2\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "edit")
    code, out = run_pr(repo, capsys)
    assert code == 0 and "FD011" not in out


def test_pr_adding_misspelled_name_in_exempt_folders_passes(tmp_path: Path, capsys):
    repo = make_repo(tmp_path, {"Workspaces/X/a.fmw": "DEFAULT_MACRO S 1\n"})
    add(repo, "Resources/Shared/b_Complete.fmw")
    add(repo, "Workspaces/AcceleratorES/c_Completo.fmw")
    code, out = run_pr(repo, capsys)
    assert code == 0
    assert "FD011" not in out
