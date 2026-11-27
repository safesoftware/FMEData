"""KNOW-2855: FD004 (workspace pairs), FD007 (unused data), and FT004 (data listed in the lesson)."""

import json
import subprocess
from pathlib import Path

import pytest

from fmedata_checks.checks_fd import complete_base, fd004, fd007, starting_partners
from fmedata_checks.checks_ft import ft004
from fmedata_checks.lessons import exercises, latest_versions, parse_lesson
from fmedata_checks.tree import RepoTree
from fmedata_checks.workspace import parse_workspace

S3 = "https://s3.amazonaws.com/FMEData/FMEData/"


# ---- FD004: a complete workspace has its starting workspace where the exercise needs one


@pytest.mark.parametrize("stem, base", [
    ("a-complete", "a"),
    ("a--complete", "a"),
    ("Ex3.1_Writing_Completed", "ex3.1writing"),
    ("ReadData-Complete", "readdata"),
    ("ReadDataComplete", "readdata"),
    ("Ejercicio1_Completo", "ejercicio1"),
    ("park_trees_complete", "parktrees"),
    ("Chapter4Exercise8.Complete", "chapter4exercise8"),
    ("handle-nulls-complete-advanced", "handlenullsadvanced"),
    ("CreateAWorkOrder_Complete_2023.0", "createaworkorder2023.0"),
])
def test_complete_base_accepts_every_spelling(stem, base):
    assert complete_base(stem) == base


@pytest.mark.parametrize("stem", ["incomplete", "a", "complete", "Complete Workspace - Part 1", "completeness-check"])
def test_complete_base_rejects_non_complete_names(stem):
    assert complete_base(stem) is None


@pytest.mark.parametrize("complete, starting", [
    ("W/a-complete.fmw", "W/a.fmw"),
    ("W/Ex2.0_Reading_Completed.fmw", "W/Ex2.0_Reading_Begin.fmw"),
    ("W/Ejercicio1_Completo.fmw", "W/Ejercicio1_Inicio.fmw"),
    ("W/Exercise1_Complete.fmw", "W/Exercise1_blank.fmw"),
    ("W/Vendeurs-Complete.fmw", "W/Vendeurs-Start.fmw"),
    ("W/a-complete.fmwt", "W/A.fmw"),
    ("W/x-complete-advanced.fmw", "W/x-advanced.fmw"),
])
def test_starting_partner_found_across_spellings(complete, starting):
    assert starting_partners(complete, [complete, starting, "W/other.fmw", "V/a.fmw"]) == [starting]


def test_starting_partner_must_be_in_the_same_folder():
    assert starting_partners("W/a-complete.fmw", ["W/a-complete.fmw", "V/a.fmw"]) == []


def _lesson(course, resources, step1="<p>Generate a new workspace.</p>", title="Ex"):
    return parse_lesson(f"2026.2/p/{course}/{title}/index.html",
                        f"<h2>Resources</h2>{resources}<h2>Exercise</h2><h3>1) Start</h3>{step1}<h3>2) Next</h3>")


def _res(complete, starting=None):
    items = f'<li><a href="{S3}{complete}">Complete workspace</a></li>'
    if starting:
        items = f'<li><a href="{S3}{starting}">Starting workspace</a></li>' + items
    return f"<ul>{items}</ul>"


def _fd004(paths, lessons):
    tree = RepoTree.from_paths(paths)
    return fd004(paths, exercises(lessons, latest_versions(lessons)), tree)


def test_fd004_exercise_starts_from_a_workspace_that_is_missing():
    paths = ["W/a-complete.fmw"]
    found = _fd004(paths, [_lesson("C 2026.2", _res("W/a-complete.fmw", "W/a.fmw"))])
    assert [(f.check_id, f.path, f.severity) for f in found] == [("FD004", "W/a-complete.fmw", "warning")]
    assert "W/a.fmw" in found[0].message and "C 2026.2" in found[0].message


def test_fd004_step1_opens_a_starting_workspace_resources_doesnt_list():
    paths = ["W/a-complete.fmw"]
    lesson = _lesson("C 2026.2", _res("W/a-complete.fmw"), step1="<p>Open the starting workspace.</p>")
    found = _fd004(paths, [lesson])
    assert [f.check_id for f in found] == ["FD004"] and "Step 1" in found[0].message


def test_fd004_blank_canvas_exercise_needs_no_starting_workspace():
    assert _fd004(["W/a-complete.fmw"], [_lesson("C 2026.2", _res("W/a-complete.fmw"))]) == []


def test_fd004_exercise_starting_from_another_existing_workspace_is_fine():
    paths = ["W/b-complete.fmw", "W/a-complete.fmw"]
    assert _fd004(paths, [_lesson("C 2026.2", _res("W/b-complete.fmw", "W/a-complete.fmw"))]) == []


def test_fd004_unlinked_complete_workspace_is_not_guessed_at():
    assert _fd004(["W/a-complete.fmw"], []) == []


def test_fd004_paired_workspace_is_fine_even_if_the_lesson_links_another_name():
    # The lesson's broken starting link is FT003's finding, not this one.
    paths = ["W/a-complete.fmw", "W/a.fmw"]
    assert _fd004(paths, [_lesson("C 2026.2", _res("W/a-complete.fmw", "W/old-name.fmw"))]) == []


def test_fd004_older_course_version_only_is_a_notice():
    lessons = [_lesson("C 2025.1", _res("W/a-complete.fmw", "W/a.fmw")), _lesson("C 2026.2", "<p>x</p>")]
    found = _fd004(["W/a-complete.fmw"], lessons)
    assert [f.severity for f in found] == ["notice"]


# ---- FD007: data files no workspace or lesson uses

DATA = ["Data/Parks/Parks.shp", "Data/Parks/Parks.dbf", "Data/Parks/Parks.prj",
        "Data/Parks.zip",
        "Data/Contours/J10.shp", "Data/Contours/J10.dbf", "Data/Contours/J11.shp",
        "Data/Planning/owners.json", "Data/Planning/owners1.json",
        "Data/City/CityProperties.zip",
        "Data/Map/Map.gdb/a0001.gdbtable", "Data/Map/Map.gdb.zip",
        "Data/OSM/a.osm", "Data/OSM/b.osm",
        "Workspaces/W/x.fmw", "Resources/R/unused.csv"]


def _fd007(refs):
    return {f.path: f for f in fd007(RepoTree.from_paths(DATA), refs)}


def test_fd007_lists_unused_data_only_under_data():
    found = _fd007([])
    assert "Resources/R/unused.csv" not in found and "Workspaces/W/x.fmw" not in found
    assert all(f.check_id == "FD007" and f.severity == "notice" for f in found.values())


def test_fd007_a_used_file_brings_its_siblings_and_folder_zip():
    found = _fd007(["data/parks/parks.shp"])  # case doesn't matter
    assert not any(p.startswith("Data/Parks") for p in found)


def test_fd007_a_wholly_unused_folder_is_one_finding():
    found = _fd007([])
    assert "Data/Contours/" in found and "2 datasets" in found["Data/Contours/"].message
    assert not any(p.startswith("Data/Contours/J") for p in found)


def test_fd007_partly_used_folder_lists_each_unused_dataset():
    found = _fd007(["Data/Planning/owners.json"])
    assert "Data/Planning/owners1.json" in found and "Data/Planning/owners.json" not in found


def test_fd007_folder_wildcard_and_zip_references_count():
    found = _fd007(["Data/OSM", "Data/Contours/*.shp", "Data/Map/Map.gdb.zip"])
    assert not any(p.startswith(("Data/OSM", "Data/Contours", "Data/Map")) for p in found)


def test_fd007_reading_inside_a_folder_zip_uses_the_zip():
    assert "Data/City/CityProperties.zip" not in _fd007(["Data/City/CityProperties/CityProperties.shp"])


def test_fd007_a_reference_to_data_itself_uses_nothing():
    assert "Data/Planning/" in _fd007(["Data"])


def test_fd007_message_never_says_delete():
    for f in _fd007([]).values():
        assert "delete" not in f.message.lower()


# ---- FT004: data the complete workspace reads is named in the lesson

WS_TEXT = ("DEFAULT_MACRO A C:\\FMEData\\Data\\Culture\\PublicArt.xlsx\n"
           "DEFAULT_MACRO B C:\\FMEData\\Data\\Orthophotos\\02-03-HI.tif\n"
           "DEFAULT_MACRO C C:\\FMEData\\Data\\Map\\Map.gdb.zip\n"
           "DEFAULT_MACRO D C:\\FMEData\\Data\\Parks.zip\n"
           "DEFAULT_MACRO E C:\\FMEData\\Output\\result.csv\n"
           "DEFAULT_MACRO F C:\\FMEData\\Workspaces\\W\\other.fmw\n")
WORKSPACES = {"W/a-complete.fmw": parse_workspace("W/a-complete.fmw", WS_TEXT),
              "W/a.fmw": parse_workspace("W/a.fmw", "DEFAULT_MACRO A C:\\FMEData\\Data\\Culture\\PublicArt.xlsx\n")}
LISTED = ("<li>Orthophotos.zip C:\\FMEData\\Data\\Orthophotos.zip</li><li>Map.gdb C:\\FMEData\\Data\\Map\\Map.gdb</li>"
          "<li>Parks C:\\FMEData\\Data\\Parks\\Parks.tab</li>")


def _ft004(extra, starting=None, current=True):
    lesson = _lesson("C 2026.2", _res("W/a-complete.fmw", starting).replace("</ul>", extra + "</ul>"))
    return ft004(lesson, WORKSPACES, current)


def test_ft004_flags_data_the_lesson_never_names():
    found = _ft004(LISTED)
    assert [(f.check_id, f.severity) for f in found] == [("FT004", "warning")]
    assert "Data/Culture/PublicArt.xlsx" in found[0].message and "W/a-complete.fmw" in found[0].message


def test_ft004_file_name_anywhere_in_the_lesson_counts():
    assert _ft004(LISTED + "<li>PublicArt.xlsx</li>") == []


def test_ft004_link_to_the_file_counts():
    assert _ft004(LISTED + f'<li><a href="{S3}Data/Culture/PublicArt.xlsx">Public art</a></li>') == []


def test_ft004_says_when_the_starting_workspace_already_reads_it():
    found = _ft004(LISTED, starting="W/a.fmw")
    assert "starting workspace already reads it" in found[0].message


def test_ft004_only_current_course_versions():
    assert _ft004(LISTED, current=False) == []


def test_ft004_lesson_without_complete_workspace_is_skipped():
    lesson = _lesson("C 2026.2", "<p>No workspaces here.</p>")
    assert ft004(lesson, WORKSPACES, True) == []


# ---- the nightly report runs all three


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_cli_lessons_reports_fd004_fd007_ft004(tmp_path: Path):
    from fmedata_checks.__main__ import main
    repo = tmp_path / "repo"
    (repo / "Data" / "Culture").mkdir(parents=True)
    (repo / "Data" / "Culture" / "PublicArt.xlsx").write_text("x", encoding="utf-8")
    (repo / "Data" / "Spare.csv").write_text("x", encoding="utf-8")
    (repo / "Workspaces").mkdir()
    (repo / "Workspaces" / "a-complete.fmw").write_text(
        "DEFAULT_MACRO A C:\\FMEData\\Data\\Culture\\PublicArt.xlsx\n", encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-q", "-m", "base")
    page = tmp_path / "FMETraining" / "2026.2" / "p" / "Course 2026.2" / "Exercise_ A" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<h2>Resources</h2><p>Starting workspace | C:\\FMEData\\Workspaces\\a.fmw</p>"
                    "<p>Complete workspace | C:\\FMEData\\Workspaces\\a-complete.fmw</p>", encoding="utf-8")
    cfg = tmp_path / "checks.toml"
    cfg.write_text('enforce = []\n[exempt]\n"Resources/" = "shared"\n', encoding="utf-8")
    out = tmp_path / "out"
    main(["lessons", "--repo", str(repo), "--fmetraining", str(tmp_path / "FMETraining"), "--out", str(out),
          "--no-network", "--config", str(cfg)])
    found = json.loads((out / "findings.json").read_text(encoding="utf-8"))["findings"]
    by_id = {f["check_id"]: f["path"] for f in found if f["check_id"] in ("FD004", "FD007", "FT004")}
    assert by_id == {"FD004": "Workspaces/a-complete.fmw", "FD007": "Data/Spare.csv",
                     "FT004": "2026.2/p/Course 2026.2/Exercise_ A/index.html"}


def test_complete_base_tries_each_complete_in_the_name():
    assert complete_base("Ex1-Incomplete-Complete") == "ex1incomplete"
    assert complete_base("Ex1-incomplete-complete") == "ex1incomplete"


def test_fd004_lesson_spelling_may_differ_in_case_from_the_repo():
    paths = ["Workspaces/Ex1-Complete.fmw"]
    lesson = _lesson("C 2026.2", _res("workspaces/Ex1-Complete.fmw", "Workspaces/ex1-start.fmw"))
    assert [f.path for f in _fd004(paths, [lesson])] == ["Workspaces/Ex1-Complete.fmw"]


def test_ft004_a_name_inside_a_longer_name_does_not_count():
    assert len(_ft004(LISTED + "<li>MainPublicArt.xlsx</li>")) == 1


def test_ft004_a_named_folder_names_the_files_in_it():
    # LISTED names Orthophotos.zip; drop it and name the plain folder instead
    folder_only = LISTED.replace("<li>Orthophotos.zip C:\\FMEData\\Data\\Orthophotos.zip</li>",
                                 "<li>C:\\FMEData\\Data\\Orthophotos</li>")
    assert _ft004(folder_only + "<li>PublicArt.xlsx</li>") == []


def test_ft004_naming_data_itself_names_nothing():
    found = _ft004(LISTED + "<li>C:\\FMEData\\Data</li>")
    assert [f.check_id for f in found] == ["FT004"]


def test_fd004_step1_naming_an_existing_workspace_is_a_start():
    paths = ["W/a-complete.fmw", "Workspaces/W/ex2-complete.fmw"]
    lesson = _lesson("C 2026.2", _res("W/a-complete.fmw"),
                     step1="<p>Open the starting workspace you saved in Exercise 2, "
                           "C:\\FMEData\\Workspaces\\W\\ex2-complete.fmw.</p>")
    assert _fd004(paths, [lesson]) == []


def test_fd004_step1_naming_a_missing_workspace_is_still_reported():
    paths = ["W/a-complete.fmw"]
    lesson = _lesson("C 2026.2", _res("W/a-complete.fmw"),
                     step1="<p>Open the starting workspace C:\\FMEData\\Workspaces\\W\\gone.fmw.</p>")
    assert [f.check_id for f in _fd004(paths, [lesson])] == ["FD004"]
