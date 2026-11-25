from pathlib import Path

from fmedata_checks.lessons import is_current, iter_lessons, latest_versions, parse_lesson

S3 = "https://s3.amazonaws.com/FMEData/FMEData/Workspaces/ADT/"

EXERCISE = f"""<h2 id="objectives">Objectives</h2><ul><li>Do a thing.</li></ul>
<h2 id="resources">Resources</h2>
<ul>
<li><a href="{S3}exercise-a.fmw" target="_blank">Starting workspace</a>
<ul><li>C:\\FMEData\\Workspaces\\ADT\\exercise-a.fmw</li></ul></li>
<li><a href="{S3}exercise-a-complete.fmw" target="_blank">Complete workspace</a>
<ul><li>C:\\FMEData\\Workspaces\\ADT\\exercise-a-complete.fmw</li></ul></li>
<li><a href="https://s3.amazonaws.com/FMEData/FMEData/Data/Transportation/Cycling.zip">Bike routes</a>
<ul><li>C:\\FMEData\\Data\\Transportation\\Cycling.zip</li></ul></li>
</ul>
<h2 id="introduction">Introduction</h2><p>See https://support.safe.com/s/article/x for help.</p>
"""

COMPLETE_ONLY = """<h2>Resources</h2><ul>
<li><a href="https://s3.amazonaws.com/FMEData/FMEData/Workspaces/ADT/b-complete.fmw">Complete workspace</a></li>
</ul><h2>Introduction</h2><p>Create a new blank workspace.</p>"""

TEXT_FORMAT = r"""<h2>Resources</h2><p>Starting workspace | C:\FMEData\Workspaces\X\c.fmw</p>
<p>Complete workspace | C:\FMEData\Workspaces\X\c-complete.fmw</p><h2>Steps</h2>"""

REL = "2026.2/fme-form-advanced/Compare Workspaces 2025.1/Exercise_ Compare Workspaces/index.html"


def test_parse_exercise_resources():
    lesson = parse_lesson(REL, EXERCISE)
    assert lesson.is_exercise and lesson.parsed
    assert lesson.starting == ["Workspaces/ADT/exercise-a.fmw"]
    assert lesson.complete == ["Workspaces/ADT/exercise-a-complete.fmw"]
    assert "Data/Transportation/Cycling.zip" in {r.rel for r in lesson.local_refs}
    assert [r.raw for r in lesson.web_refs] == ["https://support.safe.com/s/article/x"]


def test_parse_complete_only_exercise():
    lesson = parse_lesson(REL, COMPLETE_ONLY)
    assert lesson.parsed and lesson.starting == [] and lesson.complete == ["Workspaces/ADT/b-complete.fmw"]


def test_parse_text_format_resources():
    lesson = parse_lesson(REL, TEXT_FORMAT)
    assert lesson.starting == ["Workspaces/X/c.fmw"]
    assert lesson.complete == ["Workspaces/X/c-complete.fmw"]


def test_parse_plain_lesson():
    lesson = parse_lesson("2026.2/p/Course 2026.2/Intro/index.html", "<p>Hello</p>")
    assert not lesson.is_exercise and lesson.parsed


def test_exercise_without_resources_not_parsed():
    lesson = parse_lesson(REL, "<h2>Introduction</h2><p>No resources here.</p>")
    assert lesson.is_exercise and not lesson.parsed


def test_course_version_from_folder_not_archive():
    lesson = parse_lesson(REL, "")
    assert (lesson.version, lesson.course_version, lesson.course_base) == ("2026.2", "2025.1", "Compare Workspaces")
    assert lesson.title == "Exercise_ Compare Workspaces"


def test_course_without_version_suffix():
    lesson = parse_lesson("2026.2/mcp/MCP and FME/Intro/index.html", "")
    assert lesson.course_version is None and lesson.course_base == "MCP and FME"


def test_latest_versions():
    old = parse_lesson("2026.2/p/Compare Workspaces 2025.1/L/index.html", "")
    new = parse_lesson("2026.2/p/Compare Workspaces 2026.2/L/index.html", "")
    newer = parse_lesson("2027.1/p/Compare Workspaces 2026.10/L/index.html", "")
    assert latest_versions([old, new]) == {"Compare Workspaces": "2026.2"}
    latest = latest_versions([old, new, newer])
    assert latest == {"Compare Workspaces": "2026.10"}
    assert not is_current(old, latest) and is_current(newer, latest)


def test_iter_lessons_skips_ignored_courses(tmp_path: Path):
    for course in ("Clone of Transform Data 2025.0", "SM TEST - Clone of Connect 2025.0", "Transform Data 2026.1"):
        p = tmp_path / "2026.2" / "p" / course / "L" / "index.html"
        p.parent.mkdir(parents=True)
        p.write_text("<p>x</p>", encoding="utf-8")
    kept = [l.course for l in iter_lessons(tmp_path, ignore_courses=["Clone of *", "*TEST*"])]
    assert kept == ["Transform Data 2026.1"]


def test_iter_lessons_skips_non_version_dirs(tmp_path: Path):
    for rel in (REL, ".github/x/y/z/index.html", "2026.2/p/C 2026.2/L/images/index.html"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(EXERCISE, encoding="utf-8")
    assert [lesson.rel_html for lesson in iter_lessons(tmp_path)] == [REL]
