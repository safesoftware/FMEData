"""FD004 on pull requests, from the exercise list the nightly report publishes in findings.json."""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fmedata_checks.checks_fd import fd004_changes
from fmedata_checks.gitdiff import Change
from fmedata_checks.lessons import Exercise, exercises, latest_versions, parse_lesson, read_exercises
from fmedata_checks.reports import build_reports
from fmedata_checks.tree import RepoTree

S3 = "https://s3.amazonaws.com/FMEData/FMEData/"


def _lesson(course, starting, complete, step1="<p>Generate a new workspace.</p>"):
    items = f'<li><a href="{S3}{complete}">Complete workspace</a></li>'
    if starting:
        items = f'<li><a href="{S3}{starting}">Starting workspace</a></li>' + items
    return parse_lesson(f"2026.2/p/{course}/Ex/index.html",
                        f"<h2>Resources</h2><ul>{items}</ul><h2>Exercise</h2><h3>1) Start</h3>{step1}<h3>2) Next</h3>")


EX = Exercise("2026.2 / C 2026.2 / Ex", True, ("W/a.fmw",), ("W/a-complete.fmw",), False)


def test_exercises_lists_only_lessons_with_a_complete_workspace():
    lessons = [_lesson("C 2026.2", "W/a.fmw", "W/a-complete.fmw"), parse_lesson("2026.2/p/C 2026.2/Intro/index.html", "<p>x</p>"),
               _lesson("C 2025.1", None, "W/b-complete.fmw", step1="<p>Open the starting workspace.</p>")]
    found = exercises(lessons, latest_versions(lessons))
    assert found == [EX, Exercise("2026.2 / C 2025.1 / Ex", False, (), ("W/b-complete.fmw",), True)]


def test_report_publishes_exercises_and_pr_reads_them_back(tmp_path: Path):
    build_reports([], [], {}, {}, tmp_path, datetime.now(timezone.utc), exercises=[EX])
    data = json.loads((tmp_path / "findings.json").read_text(encoding="utf-8"))
    assert data["exercises"] == [{"lesson": EX.label, "current": True, "starting": ["W/a.fmw"],
                                  "complete": ["W/a-complete.fmw"]}]  # empty and false fields are left out
    assert read_exercises(str(tmp_path / "findings.json")) == ([EX], False)


def test_read_exercises_missing_old_format_and_stale(tmp_path: Path):
    assert read_exercises(str(tmp_path / "nope.json")) == (None, True)
    old_format = tmp_path / "old.json"
    old_format.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "lesson_index": {}}),
                          encoding="utf-8")
    assert read_exercises(str(old_format)) == (None, False)
    stale = tmp_path / "stale.json"
    when = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()
    stale.write_text(json.dumps({"generated_at": when, "exercises": []}), encoding="utf-8")
    assert read_exercises(str(stale)) == ([], True)


def test_pr_adding_a_complete_workspace_whose_exercise_starts_from_a_missing_one():
    tree = RepoTree.from_paths(["W/a-complete.fmw"])
    found = fd004_changes([Change("A", "W/a-complete.fmw", None)], [EX], tree)
    assert [(f.check_id, f.path, f.severity) for f in found] == [("FD004", "W/a-complete.fmw", "warning")]


def test_pr_removing_a_starting_workspace_reports_its_complete_one():
    tree = RepoTree.from_paths(["W/a-complete.fmw"])
    found = fd004_changes([Change("D", "W/a.fmw", None)], [EX], tree)
    assert [f.path for f in found] == ["W/a-complete.fmw"]


def test_pr_renaming_a_complete_workspace_keeps_its_lessons():
    tree = RepoTree.from_paths(["W/renamed-complete.fmw"])
    found = fd004_changes([Change("R", "W/renamed-complete.fmw", "W/a-complete.fmw")], [EX], tree)
    assert [f.path for f in found] == ["W/renamed-complete.fmw"]


def test_pr_with_both_workspaces_or_unrelated_changes_is_fine():
    both = RepoTree.from_paths(["W/a-complete.fmw", "W/a.fmw"])
    assert fd004_changes([Change("A", "W/a-complete.fmw", None)], [EX], both) == []
    only_complete = RepoTree.from_paths(["W/a-complete.fmw"])
    assert fd004_changes([Change("M", "W/a-complete.fmw", None), Change("D", "Data/x.csv", None)], [EX],
                         only_complete) == []


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "W").mkdir(parents=True)
    (repo / "W" / "a.fmw").write_text("x\n", encoding="utf-8")
    (repo / "W" / "a-complete.fmw").write_text("x\n", encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "branch", "base")
    git(repo, "rm", "-q", "W/a.fmw")
    git(repo, "commit", "-q", "-m", "remove the starting workspace")
    return repo


def _run(repo: Path, tmp_path: Path, index: Path, capsys) -> str:
    from fmedata_checks.__main__ import main
    cfg = tmp_path / "checks.toml"
    cfg.write_text('enforce = []\n[exempt]\n"Resources/" = "shared"\n', encoding="utf-8")
    assert main(["pr", "--repo", str(repo), "--base", "base", "--index", str(index), "--config", str(cfg)]) == 0
    return capsys.readouterr().out


def test_cli_pr_warns_with_fd004(tmp_path: Path, capsys):
    index = tmp_path / "findings.json"
    build_reports([], [], {}, {}, tmp_path, datetime.now(timezone.utc),
                  exercises=[Exercise("2026.2 / C 2026.2 / Ex", True, ("W/a.fmw",), ("W/a-complete.fmw",), False)])
    out = _run(_repo(tmp_path), tmp_path, index, capsys)
    assert "::warning file=W/a-complete.fmw::FD004" in out


def test_cli_pr_skips_fd004_without_a_usable_index(tmp_path: Path, capsys):
    out = _run(_repo(tmp_path), tmp_path, tmp_path / "missing.json", capsys)
    assert "FD004" not in out.split("FD004 skipped")[0] and "FD004 skipped" in out


def test_pr_removing_the_starting_workspace_a_step1_exercise_opens():
    # the lesson lists only the complete workspace and opens "the starting workspace" in Step 1
    ex = Exercise("2026.2 / C 2026.2 / Ex", True, (), ("W/a-complete.fmw",), True)
    tree = RepoTree.from_paths(["W/a-complete.fmw"])
    found = fd004_changes([Change("D", "W/a.fmw", None)], [ex], tree)
    assert [(f.check_id, f.path) for f in found] == [("FD004", "W/a-complete.fmw")]


def test_read_exercises_rejects_a_path_that_is_not_a_list(tmp_path: Path):
    p = tmp_path / "f.json"
    p.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
                             "exercises": [{"lesson": "L", "complete": ["W/a-complete.fmw"], "starting": "W/a.fmw"}]}),
                 encoding="utf-8")
    assert read_exercises(str(p))[0] is None
