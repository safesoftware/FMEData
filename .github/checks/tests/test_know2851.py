"""KNOW-2851: lower-severity findings from the PR #10 and #11 reviews."""

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fmedata_checks import reports
from fmedata_checks.checks_fd import fd010
from fmedata_checks.gitdiff import Change, added_lines
from fmedata_checks.lessons import parse_lesson
from fmedata_checks.model import CHECKS, PR_ONLY, Finding, annotation
from fmedata_checks.tree import RepoTree


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_added_line_starting_with_plus_plus_is_kept(tmp_path: Path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "branch", "base")
    (tmp_path / "a.txt").write_text("one\n++token\n", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "edit")
    assert added_lines(tmp_path, "base", "a.txt") == [(2, "++token")]


def test_literal_bracket_file_name_resolves():
    tree = RepoTree.from_paths(["Data/Roads[2020].shp"])
    assert tree.resolve("Data/Roads[2020].shp") == "exact"
    assert tree.resolve("data/roads[2020].shp") == "case"


def test_annotation_escapes_workflow_command_characters():
    f = Finding("FD001", "Data/Parks, 2020:a.fmw", 3, "100% wrong\nsecond line", "warning")
    assert annotation(f) == (
        "::warning file=Data/Parks%2C 2020%3Aa.fmw,line=3::FD001 100%25 wrong%0Asecond line (see CHECKS.md#fd001)")


def test_fd010_linked_dataset_folder_counts_its_files():
    idx = {"Data/CommunityMapping/CommunityMap.gdb": ["2026.2 / C 2026.2 / L"], "Data": ["2026.2 / C 2026.2 / M"]}
    found = fd010([Change("D", "Data/CommunityMapping/CommunityMap.gdb/a00000001.gdbtable", None),
                   Change("D", "Data/Other/x.csv", None)], idx, stale=False, current=idx)
    assert [(f.path, f.severity) for f in found] == [
        ("Data/CommunityMapping/CommunityMap.gdb/a00000001.gdbtable", "error")]


def test_fd010_case_only_rename_checks_wildcards_case_sensitively():
    idx = {"Data/P*.shp": ["2026.2 / C 2026.2 / L"]}
    found = fd010([Change("R", "Data/parks.shp", "Data/Parks.shp")], idx, stale=False, current=idx)
    assert [f.severity for f in found] == ["error"]


def test_broken_links_page_labels_case_mismatch(tmp_path: Path):
    lesson = parse_lesson("2026.2/p/C 2026.2/L/index.html", "<p>x</p>")
    finding = Finding("FT002", lesson.rel_html, None,
                      "https://s3.amazonaws.com/FMEData/FMEData/data/x.zip differs only in case from Data/x.zip; "
                      "S3 links are case-sensitive", "warning")
    reports.build_reports([lesson], [finding], {}, {}, tmp_path, datetime.now(timezone.utc))
    page = (tmp_path / "broken-links.html").read_text(encoding="utf-8")
    assert "case mismatch" in page and "not in FMEData" not in page


def test_pr_only_lives_with_the_check_registry():
    assert PR_ONLY <= set(CHECKS) and PR_ONLY == {"FD006", "FD010"}


def test_unregistered_check_id_has_no_empty_summary(tmp_path: Path):
    finding = Finding("FX999", "a.fmw", None, "m", "warning")
    reports.build_reports([], [finding], {}, {}, tmp_path, datetime.now(timezone.utc))
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "<small>.</small>" not in page and "FX999" in page
