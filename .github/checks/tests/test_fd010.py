import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fmedata_checks.checks_fd import fd010
from fmedata_checks.gitdiff import Change
from fmedata_checks.lessons import lesson_index, parse_lesson, read_index, write_index

PAGE = """<h2>Resources</h2><ul>
<li><a href="https://s3.amazonaws.com/FMEData/FMEData/Workspaces/X/exercise-old.fmw">Starting workspace</a></li>
</ul><p>C:\\FMEData\\Data\\Parks\\Parks.shp</p>"""

LESSON = parse_lesson("2026.2/adv/Custom Transformers 2025.1/Exercise_ Build/index.html", PAGE)
IDX = lesson_index([LESSON])


def test_lesson_index_maps_files_to_lessons():
    assert IDX["Workspaces/X/exercise-old.fmw"] == ["2026.2 / Custom Transformers 2025.1 / Exercise_ Build"]
    assert IDX["Data/Parks/Parks.shp"] == ["2026.2 / Custom Transformers 2025.1 / Exercise_ Build"]


def test_fd010_rename_of_linked_file():
    found = fd010([Change("R", "Workspaces/X/new.fmw", "Workspaces/X/exercise-old.fmw")], IDX, stale=False)
    assert len(found) == 1
    f = found[0]
    assert (f.check_id, f.severity, f.path) == ("FD010", "error", "Workspaces/X/exercise-old.fmw")
    assert "Custom Transformers 2025.1 / Exercise_ Build" in f.message


def test_fd010_unlinked_delete_ok():
    assert fd010([Change("D", "Data/Unused.csv", None)], IDX, stale=False) == []


def test_fd010_ignores_added_and_modified():
    assert fd010([Change("M", "Data/Parks/Parks.shp", None)], IDX, stale=False) == []


def test_fd010_stale_index_warns():
    found = fd010([Change("D", "Data/Parks/Parks.shp", None)], IDX, stale=True)
    assert found[0].severity == "warning" and "lesson index is stale" in found[0].message


def test_read_index_missing_is_stale(tmp_path: Path):
    assert read_index(str(tmp_path / "nope.json")) == ({}, True)


def test_write_then_read_index_fresh(tmp_path: Path):
    p = tmp_path / "findings.json"
    write_index(IDX, p)
    idx, stale = read_index(str(p))
    assert idx == IDX and not stale


def test_read_index_old_is_stale(tmp_path: Path):
    p = tmp_path / "findings.json"
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    p.write_text(json.dumps({"generated_at": old, "lesson_index": IDX}), encoding="utf-8")
    idx, stale = read_index(str(p), max_age_days=7)
    assert idx == IDX and stale
