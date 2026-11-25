from fmedata_checks.checks_fd import fd005, fd011
from fmedata_checks.checks_ft import fme_version, ft006, ft007
from fmedata_checks.lessons import parse_lesson, previous_version
from fmedata_checks.model import Config
from fmedata_checks.workspace import Workspace

S3 = "https://s3.amazonaws.com/FMEData/FMEData/"


def page(course, workspace):
    html = f'<h2>Resources</h2><ul><li><a href="{S3}{workspace}">Complete workspace</a></li></ul>'
    return parse_lesson(f"2026.2/adv/{course}/Exercise_ E/index.html", html)


def wss(build):
    return {"Workspaces/X/a-complete.fmw": Workspace("Workspaces/X/a-complete.fmw", build, 1)}


def test_fme_version_parse():
    assert fme_version("2026.2.0.0") == (2026, 2)
    assert fme_version(None) is None


def test_previous_version():
    a, b, c = page("C 2025.1", "x"), page("C 2026.1", "x"), page("C 2026.2", "x")
    assert previous_version(c, [a, b, c]) == "2026.1"
    assert previous_version(a, [a, b, c]) is None


def test_ft006_newer_than_course():
    found = ft006(page("C 2025.1", "Workspaces/X/a-complete.fmw"), wss("2026.2.0.0"), current=True,
                  previous_version=None)
    assert len(found) == 1 and found[0].severity == "warning"
    assert "2026.2" in found[0].message and "2025.1" in found[0].message


def test_ft006_same_or_older_ok():
    lesson = page("C 2026.2", "Workspaces/X/a-complete.fmw")
    assert ft006(lesson, wss("2026.1.0.0"), current=True, previous_version="2026.1") == []
    found = ft006(lesson, wss("2024.1.0.0"), current=True, previous_version="2026.1")
    assert [(f.severity, "not updated" in f.message) for f in found] == [("notice", True)]


def test_ft006_unknown_build_or_missing_workspace_skipped():
    lesson = page("C 2026.2", "Workspaces/X/a-complete.fmw")
    assert ft006(lesson, wss(None), current=True, previous_version=None) == []
    assert ft006(lesson, {}, current=True, previous_version=None) == []


def test_ft007_legacy_link():
    lesson = page("C 2025.1", "Workspaces/AdvancedDataTransformation/exercise-handle-null-and-missing-values.fmw")
    found = ft007(lesson, current=False)
    assert [(f.check_id, f.severity) for f in found] == [("FT007", "notice")]


def test_fd005_pr_vs_report():
    assert [f.severity for f in fd005(["Workspaces/X/exercise-x.fmw"], pr_added=True)] == ["warning"]
    assert [f.severity for f in fd005(["Workspaces/X/exercise-x.fmw"], pr_added=False)] == ["notice"]
    assert fd005(["Workspaces/X/x.fmw", "Data/exercise-data.csv"], pr_added=False) == []


def test_fd011_variants():
    cfg = Config()
    for name in ["a-Complete.fmw", "a_Completed.fmw", "a_Complete.fmw", "aComplete.fmw",
                 "a--complete.fmw", "a_complete.fmw", "a Complete.fmwt"]:
        found = fd011([f"Workspaces/X/{name}"], pr_added=False, cfg=cfg)
        assert len(found) == 1, name
        ext = name.rsplit(".", 1)[1]
        assert f"Workspaces/X/a-complete.{ext}" in found[0].message, name
    assert fd011(["Workspaces/X/a-complete.fmw", "Data/complete.csv"], pr_added=False, cfg=cfg) == []


def test_fd011_localized_suffix():
    cfg = Config(complete_suffixes=["-complete", "-completo"])
    found = fd011(["Workspaces/ES/a_Completo.fmw"], pr_added=False, cfg=cfg)
    assert "Workspaces/ES/a-completo.fmw" in found[0].message
    assert fd011(["Workspaces/ES/a-completo.fmw"], pr_added=False, cfg=cfg) == []


def test_fd011_pr_severity():
    assert fd011(["Workspaces/X/a_Complete.fmw"], pr_added=True, cfg=Config())[0].severity == "error"
