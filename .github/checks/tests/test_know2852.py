"""KNOW-2852: which course versions count as current, cross-checked against Skilljar's published catalog."""

import json
from pathlib import Path

import pytest

from fmedata_checks import courses
from fmedata_checks.__main__ import main
from fmedata_checks.lessons import current_index, is_current, iter_lessons, latest_versions, parse_lesson
from fmedata_checks.model import load_config


def lesson(rel, **kw):
    return parse_lesson(rel, "", **kw)


# --- config ---------------------------------------------------------------------------------------------------

def test_config_reads_courses_table(tmp_path: Path):
    p = tmp_path / "checks.toml"
    p.write_text('[courses]\narchived = ["Publish Workflows to the Web"]\n'
                 '[courses.current]\n"MCP and FME" = "2026.2"\n', encoding="utf-8")
    cfg = load_config(p)
    assert cfg.course_versions == {"MCP and FME": "2026.2"}
    assert cfg.archived_courses == ["Publish Workflows to the Web"]


def test_config_without_courses_table(tmp_path: Path):
    p = tmp_path / "checks.toml"
    p.write_text("enforce = []\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg.course_versions == {} and cfg.archived_courses == []


def test_config_rejects_bad_course_version(tmp_path: Path):
    p = tmp_path / "checks.toml"
    p.write_text('[courses.current]\n"MCP and FME" = "26.2"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="MCP and FME"):
        load_config(p)


def test_repo_config_lists_the_live_unversioned_courses():
    cfg = load_config(Path(__file__).resolve().parent.parent / "checks.toml")
    assert cfg.course_versions["MCP and FME"] == "2026.2"
    assert "Publish Workflows to the Web" in cfg.archived_courses


# --- lessons --------------------------------------------------------------------------------------------------

def test_unversioned_course_named_in_config_takes_its_archive_folder_version():
    versions = {"MCP and FME": "2026.2"}
    mcp = lesson("2026.2/mcp/MCP and FME/Intro/index.html", course_versions=versions)
    assert (mcp.course_base, mcp.course_version) == ("MCP and FME", "2026.2")
    other = lesson("2026.2/mcp/MCP with FME/Intro/index.html", course_versions=versions)
    assert other.course_version is None


def test_configured_unversioned_course_is_current_only_in_its_live_folder():
    versions = {"Streams - Live Online Course": "2026.2"}
    old = lesson("2025.2/streams/Streams - Live Online Course/L/index.html", course_versions=versions)
    new = lesson("2026.2/streams/Streams - Live Online Course/L/index.html", course_versions=versions)
    latest = latest_versions([old, new], current=versions)
    assert is_current(new, latest) and not is_current(old, latest)


def test_current_overrides_the_archive_newest_version():
    a = lesson("2026.1/p/Transform Data 2026.1/L/index.html")
    b = lesson("2026.2/p/Transform Data 2026.2/L/index.html")
    latest = latest_versions([a, b], current={"Transform Data": "2026.1"})
    assert is_current(a, latest) and not is_current(b, latest)


def test_archived_course_has_no_current_version():
    old = lesson("2023.0/f/Publish Workflows to the Web 2023.0/L/index.html")
    new = lesson("2024.1/f/Publish Workflows to the Web 2024.1/L/index.html")
    keep = lesson("2026.1/f/Transform Data 2026.1/L/index.html")
    latest = latest_versions([old, new, keep], archived=["Publish Workflows to the Web"])
    assert latest == {"Transform Data": "2026.1"}
    assert not is_current(new, latest) and is_current(keep, latest)


def test_archived_accepts_patterns():
    a = lesson("2024.1/f/Build Basic Automations 2024.1/L/index.html")
    assert latest_versions([a], archived=["Build Basic *"]) == {}


def test_current_index_honors_course_config():
    s3 = "https://s3.amazonaws.com/FMEData/FMEData/Workspaces/X/a.fmw"
    retired = parse_lesson("2024.1/f/Publish Workflows to the Web 2024.1/L/index.html", f'<a href="{s3}">x</a>')
    mcp = parse_lesson("2026.2/mcp/MCP and FME/L/index.html", f'<a href="{s3}">x</a>',
                       course_versions={"MCP and FME": "2026.2"})
    idx = current_index([retired, mcp], current={"MCP and FME": "2026.2"}, archived=["Publish Workflows to the Web"])
    assert idx == {"Workspaces/X/a.fmw": ["2026.2 / MCP and FME / L"]}


def test_iter_lessons_passes_course_versions(tmp_path: Path):
    p = tmp_path / "2026.2" / "mcp" / "MCP and FME" / "L" / "index.html"
    p.parent.mkdir(parents=True)
    p.write_text("<p>x</p>", encoding="utf-8")
    [found] = iter_lessons(tmp_path, course_versions={"MCP and FME": "2026.2"})
    assert found.course_version == "2026.2"


# --- deriving the config from Skilljar's catalog --------------------------------------------------------------

ARCHIVE = [
    ("2026.2", "MCP and FME"),
    ("2026.2", "MCP with FME"),
    ("2025.2", "Streams - Live Online Course"),
    ("2026.2", "Streams - Live Online Course"),
    ("2023.0", "Publish Workflows to the Web 2023.0"),
    ("2024.1", "Publish Workflows to the Web 2024.1"),
    ("2026.1", "What is FME Flow_ 2026.1"),
    ("2025.0", "What is FME Flow_ 2025.0"),
    ("2026.1", "Leverage Ordered Data 2026.1"),
    ("2026.2", "Leverage Ordered Data 2026.2"),
    ("2026.2", "Compare Workspaces 2026.2"),
    ("2025.0", "Clone of Transform Data 2025.0"),
]
CATALOG = [
    {"title": "MCP and FME", "slug": "mcp-and-fme"},
    {"title": "Streams - Live Online Course", "slug": "streams-live-online-course"},
    {"title": "Publish Workflows to the Web 2023.0", "slug": "publish-workflows-to-the-web-2023-0"},
    {"title": "Publish Workflows to the Web 2024.1", "slug": "publish-workflows-to-the-web-2024-1"},
    {"title": "What is FME Flow? 2026.1", "slug": "what-is-fme-flow"},
    {"title": "Leverage Ordered Data 2026.2", "slug": "leverage-ordered-data"},
    {"title": "Compare Workspaces 2026.1", "slug": "compare-workspaces"},
    {"title": "Compare Workspaces 2024.1", "slug": "compare-workspaces-2024-1"},
]


def test_derive_course_config():
    found = courses.derive(ARCHIVE, CATALOG, ignore_courses=["Clone of *"])
    assert found.current == {
        "Compare Workspaces": "2026.1",              # Skilljar's live version is older than the archive's newest
        "MCP and FME": "2026.2",                      # unversioned and live: its newest archive folder
        "Streams - Live Online Course": "2026.2",
    }
    assert found.archived == ["Publish Workflows to the Web"]
    assert found.renames == [("MCP and FME", "MCP and FME 2026.2"),
                             ("Streams - Live Online Course", "Streams - Live Online Course 2026.2")]


def test_archive_name_matches_folder_spelling():
    assert courses.archive_name("What is FME Flow? 2026.1") == "What is FME Flow_ 2026.1"
    assert courses.archive_name("FME & ​Esri Utility Network Migration 2019.1") == \
        "FME & Esri Utility Network Migration 2019.1"


def test_catalog_rows_accept_v1_shape():
    rows = courses.catalog_rows([{"slug": "mcp-and-fme", "course": {"title": "MCP and FME"}}])
    assert rows == [{"title": "MCP and FME", "slug": "mcp-and-fme"}]


def test_render_toml_round_trips(tmp_path: Path):
    text = courses.render_toml(courses.derive(ARCHIVE, CATALOG, ignore_courses=["Clone of *"]))
    p = tmp_path / "checks.toml"
    p.write_text(text, encoding="utf-8")
    cfg = load_config(p)
    assert cfg.course_versions["MCP and FME"] == "2026.2"
    assert cfg.archived_courses == ["Publish Workflows to the Web"]


def test_fetch_catalog_pages_and_authenticates():
    pages = {
        "https://api.skilljar.com/v1/domains/academy.safe.com/published-courses?page_size=100":
            {"next": "https://api.skilljar.com/v1/domains/academy.safe.com/published-courses?page=2",
             "results": [{"slug": "a", "course": {"title": "A 2026.1"}}]},
        "https://api.skilljar.com/v1/domains/academy.safe.com/published-courses?page=2":
            {"next": None, "results": [{"slug": "b", "course": {"title": "B"}}]},
    }
    seen = []

    def get(url, headers):
        seen.append(headers["Authorization"])
        return pages[url]

    rows = courses.fetch_catalog("academy.safe.com", "k", get=get)
    assert [r["slug"] for r in rows] == ["a", "b"]
    assert all(h.startswith("Basic ") for h in seen)


def test_courses_command_needs_a_catalog_or_key(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.delenv("SKILLJAR_API_KEY", raising=False)
    assert main(["courses", "--fmetraining", str(tmp_path)]) == 2
    assert "SKILLJAR_API_KEY" in capsys.readouterr().err


def test_courses_command_prints_config_from_a_catalog_file(tmp_path: Path, capsys):
    for version, course in ARCHIVE:
        p = tmp_path / "archive" / version / "p" / course / "L" / "index.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("<p>x</p>", encoding="utf-8")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(CATALOG), encoding="utf-8")
    assert main(["courses", "--fmetraining", str(tmp_path / "archive"), "--catalog", str(catalog)]) == 0
    out = capsys.readouterr().out
    assert '"MCP and FME" = "2026.2"' in out
    assert '"Publish Workflows to the Web"' in out
    assert "MCP and FME -> MCP and FME 2026.2" in out


# --- unversioned current courses follow the annual FME version ------------------------------------------------

from datetime import date

from fmedata_checks.checks_ft import annual_year, ft006
from fmedata_checks.workspace import Workspace

ACCEL = "2024.0/live-course/FME Accelerator/Exercise_ E/index.html"
WS = "Workspaces/X/a-complete.fmw"


def annual_lesson():
    html = f'<h2>Resources</h2><ul><li><a href="https://s3.amazonaws.com/FMEData/FMEData/{WS}">Complete workspace</a></li></ul>'
    return parse_lesson(ACCEL, html, course_versions={"FME Accelerator": "annual"})


def saved(build):
    return {WS: Workspace(WS, build, 1)}


def test_config_accepts_annual(tmp_path: Path):
    p = tmp_path / "checks.toml"
    p.write_text('[courses.current]\n"FME Accelerator" = "annual"\n', encoding="utf-8")
    assert load_config(p).course_versions == {"FME Accelerator": "annual"}
    p.write_text('[courses.current]\n"FME Accelerator" = "yearly"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="annual"):
        load_config(p)


def test_repo_config_has_fme_accelerator_annual():
    cfg = load_config(Path(__file__).resolve().parent.parent / "checks.toml")
    assert cfg.course_versions["FME Accelerator"] == "annual"


def test_annual_course_is_current_in_its_newest_folder():
    versions = {"FME Accelerator": "annual"}
    old = lesson("2023.0/live-course/FME Accelerator/L/index.html", course_versions=versions)
    new = lesson("2024.0/live-course/FME Accelerator/L/index.html", course_versions=versions)
    assert new.annual and old.annual
    latest = latest_versions([old, new], current=versions)
    assert is_current(new, latest) and not is_current(old, latest)


def test_annual_year_turns_over_on_may_1():
    assert annual_year(date(2027, 4, 30)) == 2026
    assert annual_year(date(2027, 5, 1)) == 2027
    assert annual_year(date(2027, 1, 1)) == 2026
    assert annual_year(date(2027, 12, 31)) == 2027


def test_ft006_annual_course_last_year_ok_until_april_30():
    assert ft006(annual_lesson(), saved("2026.2.0.0"), current=True, previous_version=None,
                 today=date(2027, 4, 30)) == []


def test_ft006_annual_course_needs_this_year_from_may_1():
    found = ft006(annual_lesson(), saved("2026.2.0.0"), current=True, previous_version=None, today=date(2027, 5, 1))
    assert [(f.check_id, f.severity) for f in found] == [("FT006", "warning")]
    assert "2026.2" in found[0].message and "FME 2027" in found[0].message and "April 30" in found[0].message


def test_ft006_annual_course_this_year_ok():
    assert ft006(annual_lesson(), saved("2027.0.0.0"), current=True, previous_version=None,
                 today=date(2027, 5, 1)) == []


def test_ft006_annual_course_ignores_its_folder_version():
    # The archive files it under 2024.0, but an annual course isn't "newer than the course" for a 2026 workspace.
    assert ft006(annual_lesson(), saved("2026.1.0.0"), current=True, previous_version="2023.0",
                 today=date(2026, 11, 26)) == []


def test_ft006_annual_course_older_than_last_year_warns_before_may():
    found = ft006(annual_lesson(), saved("2025.1.0.0"), current=True, previous_version=None, today=date(2027, 4, 30))
    assert len(found) == 1 and "FME 2026" in found[0].message


def test_derive_keeps_annual_courses_without_a_rename(tmp_path: Path):
    archive = [*ARCHIVE, ("2024.0", "FME Accelerator")]
    catalog = [*CATALOG, {"title": "FME Accelerator", "slug": "fme-accelerator"}]
    found = courses.derive(archive, catalog, ignore_courses=["Clone of *"], annual=["FME Accelerator"])
    assert found.current["FME Accelerator"] == "annual"
    assert "FME Accelerator" not in [old for old, _ in found.renames]
    p = tmp_path / "checks.toml"
    p.write_text(courses.render_toml(found), encoding="utf-8")
    assert load_config(p).course_versions["FME Accelerator"] == "annual"


def test_derive_drops_annual_course_no_longer_live():
    found = courses.derive(ARCHIVE + [("2024.0", "FME Accelerator")], CATALOG, annual=["FME Accelerator"])
    assert "FME Accelerator" not in found.current
