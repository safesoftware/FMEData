import subprocess
from pathlib import Path

from fmedata_checks.checks_fd import fd006
from fmedata_checks.gitdiff import Change, added_lines, changed_files


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def make_repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "a.fmw").write_text("line one\nline two\n" + "x\n" * 20, encoding="utf-8")
    (tmp_path / "keep.txt").write_text("keep\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "branch", "base")
    return tmp_path


def test_changed_files_rename(tmp_path: Path):
    repo = make_repo(tmp_path)
    git(repo, "mv", "a.fmw", "b.fmw")
    git(repo, "commit", "-q", "-m", "rename")
    assert changed_files(repo, "base") == [Change("R", "b.fmw", "a.fmw")]


def test_changed_files_delete_and_add(tmp_path: Path):
    repo = make_repo(tmp_path)
    git(repo, "rm", "-q", "keep.txt")
    (repo / "new.fmw").write_text("n\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "change")
    assert sorted(changed_files(repo, "base"), key=lambda c: c.path) == [
        Change("D", "keep.txt", None), Change("A", "new.fmw", None)]


def test_added_lines_only_new(tmp_path: Path):
    repo = make_repo(tmp_path)
    (repo / "a.fmw").write_text("line one\nNEW\nline two\n" + "x\n" * 20, encoding="utf-8")
    git(repo, "commit", "-q", "-am", "edit")
    assert added_lines(repo, "base", "a.fmw") == [(2, "NEW")]


def test_fd006_flags_each_pattern():
    # Samples are assembled at runtime so this file doesn't trip FD006 itself.
    secret = "AKIA" + "ABCDEFGHIJKLMNOP"
    lines = [
        (1, f"key={secret}"),
        (2, "aws_secret" + "_access_key = " + "x" * 40),
        (3, "token ghp" + "_" + "a" * 36),
        (4, "-----BEGIN RSA " + "PRIVATE KEY-----"),
        (5, "contact jane.doe" + "@" + "corp.test"),
        (6, "C:" + "\\Users\\jdoe\\Desktop\\x.csv"),
    ]
    found = fd006("Workspaces/a.fmw", lines)
    assert [f.line for f in found] == [1, 2, 3, 4, 5, 6]
    assert all(f.severity == "error" and f.check_id == "FD006" for f in found)
    text = " ".join(f.message for f in found)
    assert secret not in text and "jane.doe" not in text and "jdoe" not in text


def test_fd006_skips_fme_header_comment_in_workspaces():
    header = '#        "C:\\Program Files\\FME\\fme.exe" C:' + "\\Users\\jdoe\\Documents\\a.fmw"
    assert fd006("Workspaces/a.fmw", [(4, header)]) == []
    assert len(fd006("notes.txt", [(4, header)])) == 1


def test_fd006_allows_example_domain():
    assert fd006("a.fmw", [(1, "someone@example.com"), (2, "x@example.org")]) == []
