from pathlib import Path

from fmedata_checks.checks_ft import ft008
from fmedata_checks.lessons import ignored_courses, parse_lesson

S3 = "https://s3.amazonaws.com/FMEData/FMEData/Workspaces/X/"
REL = "2026.2/adv/Course 2026.2/Exercise_ E/index.html"
RES_START = f'<h2>Resources</h2><ul><li><a href="{S3}a.fmw">Starting workspace</a></li>' \
            f'<li><a href="{S3}a-complete.fmw">Complete workspace</a></li></ul>'
RES_COMPLETE = f'<h2>Resources</h2><ul><li><a href="{S3}a-complete.fmw">Complete workspace</a></li></ul>'


def lesson(resources, step1):
    return parse_lesson(REL, resources + f"<h2>Introduction</h2><p>x</p><h3>1) Start Workbench</h3>{step1}"
                                          "<h3>2) Next</h3><p>C:\\FMEData\\Workspaces\\X\\a.fmw</p>")


def messages(l):
    return [f.message for f in ft008(l, current=True)]


def test_step1_parsed():
    l = lesson(RES_START, "<p>Open the starting workspace (C:\\FMEData\\Workspaces\\X\\a.fmw).</p>")
    assert l.step1_mentions_start and l.step1_workspaces == ["Workspaces/X/a.fmw"]


def test_ft008_ok_when_step1_has_path_and_resources_list_it():
    assert messages(lesson(RES_START, "<p>Open the starting workspace (C:\\FMEData\\Workspaces\\X\\a.fmw).</p>")) == []


def test_ft008_step1_without_path():
    assert messages(lesson(RES_START, "<p>Open the&nbsp;starting workspace in FME Workbench.</p>")) == [
        "Step 1 opens the starting workspace but doesn't give its C:\\FMEData path"]


def test_ft008_resources_missing_starting():
    found = messages(lesson(RES_COMPLETE, "<p>Open the starting workspace (C:\\FMEData\\Workspaces\\X\\a.fmw).</p>"))
    assert found == ["Step 1 opens a starting workspace, but Resources doesn't list one"]


def test_ft008_step1_path_differs_from_resources():
    found = messages(lesson(RES_START, "<p>Open C:\\FMEData\\Workspaces\\X\\b.fmw.</p>"))
    assert found == ["Step 1 opens Workspaces/X/b.fmw, but Resources lists Workspaces/X/a.fmw"]


def test_ft008_blank_start_exercise_ok():
    assert messages(lesson(RES_COMPLETE, "<p>Create a new blank workspace in FME Workbench.</p>")) == []


def test_ft008_no_step1_heading_skipped_and_older_is_notice():
    no_step = parse_lesson(REL, RES_START + "<h2>Introduction</h2><p>Open the starting workspace.</p>")
    assert ft008(no_step, current=True) == []
    l = lesson(RES_START, "<p>Open the starting workspace.</p>")
    assert [f.severity for f in ft008(l, current=False)] == ["notice"]


def test_ignored_courses_listed(tmp_path: Path):
    for course in ("Clone of Transform Data 2025.0", "SM TEST - Clone of Connect 2025.0", "Transform Data 2026.1"):
        for lesson_name in ("L1", "L2"):
            p = tmp_path / "2026.2" / "p" / course / lesson_name / "index.html"
            p.parent.mkdir(parents=True)
            p.write_text("<p>x</p>", encoding="utf-8")
    assert ignored_courses(tmp_path, ["Clone of *", "*TEST*"]) == [
        "2026.2/p/Clone of Transform Data 2025.0", "2026.2/p/SM TEST - Clone of Connect 2025.0"]
