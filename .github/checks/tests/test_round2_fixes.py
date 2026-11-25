"""Regression tests for PR #10 review round 2 (defects in the round-1 fixes)."""

from fmedata_checks.checks_fd import fd006, fd010
from fmedata_checks.gitdiff import Change
from fmedata_checks.lessons import is_current, latest_versions, parse_lesson
from fmedata_checks.refs import redact


def errors(changes, idx):
    return [f.path for f in fd010(changes, idx, stale=False, current=idx) if f.severity == "error"]


def test_fd010_case_only_rename_flags_only_exact_old_spelling():
    rename = [Change("R", "Data/parks.shp", "Data/Parks.shp")]
    assert errors(rename, {"data/parks.shp": ["L"]}) == []
    assert errors(rename, {"Data/Parks.shp": ["L"]}) == ["Data/Parks.shp"]


def test_fd010_brackets_are_literal_and_star_stays_in_folder():
    assert errors([Change("D", "Data/file1.csv", None)], {"Data/file[1].csv": ["L"]}) == []
    assert errors([Change("D", "Data/Roads/Sub/a.shp", None)], {"Data/Roads/*.shp": ["L"]}) == []
    assert errors([Change("D", "Data/Roads/a.shp", None)], {"Data/Roads/*.shp": ["L"]}) == ["Data/Roads/a.shp"]


def test_unversioned_and_versioned_copies_are_judged_separately():
    unversioned = parse_lesson("2025.2/p/Compare Workspaces/L/index.html", "")
    versioned = parse_lesson("2026.0/p/Compare Workspaces 2025.1/L/index.html", "")
    latest = latest_versions([unversioned, versioned])
    assert is_current(versioned, latest)


def test_fd006_prose_about_the_users_folder_passes():
    prose = "Profiles live under C:" + "\\Users\\ by default."
    assert fd006("notes.txt", [(1, prose)]) == []
    spaced = "C:" + "\\Users\\John Smith\\Desktop\\a.csv"
    assert len(fd006("notes.txt", [(1, spaced)])) == 1


def test_redact_keeps_its_own_message_and_whole_names():
    msg = "this line adds a personal C:" + "\\Users\\… folder; the repository is public"
    assert redact(msg) == msg
    assert redact("C:" + "\\Users\\John Smith\\Desktop") == "C:" + "\\Users\\…\\Desktop"
    assert redact("Profiles live under C:" + "\\Users\\ by default.") == "Profiles live under C:" + "\\Users\\ by default."
