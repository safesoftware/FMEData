"""Regression tests for the whole-branch review findings."""

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fmedata_checks.checks_fd import fd006, fd010
from fmedata_checks.gitdiff import Change, added_lines, changed_files
from fmedata_checks.lessons import current_index, lesson_index, parse_lesson, read_index
from fmedata_checks.model import Config
from fmedata_checks.reports import build_reports
from fmedata_checks.tree import RepoTree


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def repo_with(tmp_path: Path, files: dict[str, bytes]) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "branch", "base")
    return tmp_path


def test_non_utf8_text_does_not_crash(tmp_path: Path):
    repo = repo_with(tmp_path, {"keep.txt": b"k\n"})
    (repo / "latin.csv").write_bytes("caf\xe9,na\xefve\n".encode("latin-1"))
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "latin")
    assert [n for n, _ in added_lines(repo, "base", "latin.csv")] == [1]
    assert RepoTree.from_git(repo).resolve("latin.csv") == "exact"


def test_renamed_file_shows_only_changed_lines(tmp_path: Path):
    body = "".join(f"line {i}\n" for i in range(30)).encode()
    repo = repo_with(tmp_path, {"a_Complete.fmw": body})
    git(repo, "mv", "a_Complete.fmw", "a-complete.fmw")
    git(repo, "commit", "-q", "-m", "rename")
    change = changed_files(repo, "base")[0]
    assert change == Change("R", "a-complete.fmw", "a_Complete.fmw")
    assert added_lines(repo, "base", change.path, old_path=change.old_path) == []


def test_fd006_decodes_workspace_text_and_warns():
    line = (10, "EMAIL_TO someone" + "<at>" + "corp.test")
    found = fd006("Workspaces/a.fmw", [line])
    assert [(f.check_id, f.severity) for f in found] == [("FD006", "warning")]
    assert fd006("notes.txt", [line]) == []


def test_fd006_plain_text_email_still_error():
    assert fd006("notes.txt", [(1, "mail someone" + "@" + "corp.test")])[0].severity == "error"


def test_fd006_aws_secret_needs_a_value():
    ref = "          aws-secret-access-key: ${{ secrets." + "AWS_SECRET" + "_ACCESS_KEY }}"
    assert fd006("ci.yml", [(1, ref)]) == []
    real = "aws_secret" + "_access_key = " + "a" * 20 + "/" + "B" * 19
    assert [f.message for f in fd006("cfg.ini", [(1, real)])] == [
        "this line adds an AWS secret key setting; the repository is public"]


def test_fd006_ignores_common_false_positives():
    lines = [(1, "icon@2x.png and logo@3x.jpg"), (2, "git" + "@github.com:safesoftware/FMEData.git"),
             (3, "C:" + "\\Users\\Default\\AppData\\x"), (4, "C:" + "\\Users\\Public\\Documents\\x")]
    assert fd006("notes.txt", lines) == []


IDX = {"Data/x.csv": ["2025.1 / Course 2025.1 / L"], "Data/y.csv": ["2026.2 / Course 2026.2 / L"]}
CURRENT = {"Data/y.csv": ["2026.2 / Course 2026.2 / L"]}


def test_fd010_respects_allow_paths():
    cfg = Config(allow_paths={"Data/y.csv": "lessons being updated this week"})
    assert fd010([Change("D", "Data/y.csv", None)], IDX, stale=False, current=CURRENT, cfg=cfg) == []


def test_fd010_fails_only_for_current_lessons():
    found = fd010([Change("D", "Data/x.csv", None), Change("D", "Data/y.csv", None)], IDX, stale=False,
                  current=CURRENT, cfg=Config())
    assert {f.path: f.severity for f in found} == {"Data/x.csv": "warning", "Data/y.csv": "error"}


def test_current_index_and_shas_written(tmp_path: Path):
    old = parse_lesson("2026.2/p/Course 2025.1/L/index.html", "<p>C:\\FMEData\\Data\\x.csv</p>")
    new = parse_lesson("2026.2/p/Course 2026.2/L/index.html", "<p>C:\\FMEData\\Data\\y.csv</p>")
    lessons = [old, new]
    assert set(current_index(lessons)) == {"Data/y.csv"}
    build_reports(lessons, [], {}, lesson_index(lessons), tmp_path, datetime.now(timezone.utc),
                  fmetraining_sha="t1", fmedata_sha="d1", current_idx=current_index(lessons))
    idx, current, stale = read_index(str(tmp_path / "findings.json"), with_current=True)
    assert set(idx) == {"Data/x.csv", "Data/y.csv"} and set(current) == {"Data/y.csv"} and not stale
    assert '"fmedata_sha": "d1"' in (tmp_path / "findings.json").read_text(encoding="utf-8")
