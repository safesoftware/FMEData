from fmedata_checks.checks_ft import ft001, ft002, ft003, ft005
from fmedata_checks.lessons import parse_lesson
from fmedata_checks.links import check_urls, classify_url
from fmedata_checks.model import Config
from fmedata_checks.tree import RepoTree

CFG = Config(bot_refusers=["support.safe.com"])
TREE = RepoTree.from_paths(["Data/Parks/Parks.shp", "Workspaces/X/a.fmw", "Workspaces/X/a-complete.fmw"])
REL = "2026.2/adv/Course 2026.2/Exercise_ E/index.html"


def lesson(html, rel=REL):
    return parse_lesson(rel, html)


def test_classify_support_403_is_bot_refused():
    assert classify_url("https://support.safe.com/s/article/x", 403, CFG) == "bot-refused"


def test_classify_localhost():
    assert classify_url("http://localhost:8080/fmeserver", None, CFG) == "local"
    assert classify_url("http://127.0.0.1/x", 200, CFG) == "local"


def test_classify_404_broken_and_ok():
    assert classify_url("https://example.com/x", 404, CFG) == "broken"
    assert classify_url("https://example.com/x", 200, CFG) == "ok"
    assert classify_url("https://example.com/x", None, CFG) == "error"


def test_check_urls_dedupes():
    calls = []

    def fetch(url):
        calls.append(url)
        return 200

    result = check_urls({"https://a.example/x", "https://a.example/x", "https://b.example/y"}, fetch, workers=2)
    assert result == {"https://a.example/x": 200, "https://b.example/y": 200}
    assert sorted(calls) == ["https://a.example/x", "https://b.example/y"]


def test_ft001_missing_local_path():
    found = ft001(lesson(r"<p>C:\FMEData\Data\Gone.csv and C:\FMEData\Data\Parks\Parks.shp</p>"), TREE, CFG, current=True)
    assert [(f.check_id, f.severity) for f in found] == [("FT001", "warning")]
    assert "Data/Gone.csv" in found[0].message and found[0].path == REL


def test_ft002_main_prefix_uses_tree():
    html = '<a href="https://s3.amazonaws.com/FMEData/FMEData/Data/Gone.zip">x</a>'
    assert [f.check_id for f in ft002(lesson(html), TREE, CFG, {}, current=True)] == ["FT002"]


def test_ft002_other_prefix_uses_statuses():
    url = "https://s3.amazonaws.com/FMEData/FMEData2022/x.zip"
    found = ft002(lesson(f'<a href="{url}">x</a>'), TREE, CFG, {url: 404}, current=True)
    assert len(found) == 1 and "404" in found[0].message
    assert ft002(lesson(f'<a href="{url}">x</a>'), TREE, CFG, {url: 200}, current=True) == []


def test_ft003_missing_complete():
    html = '<h2>Resources</h2><ul><li><a href="https://s3.amazonaws.com/FMEData/FMEData/Workspaces/X/a.fmw">Starting workspace</a></li></ul>'
    msgs = [f.message for f in ft003(lesson(html), TREE, current=True)]
    assert msgs == ["no complete workspace listed in Resources"]


def test_ft003_listed_but_not_in_tree():
    html = '<h2>Resources</h2><ul><li><a href="https://s3.amazonaws.com/FMEData/FMEData/Workspaces/X/b-complete.fmw">Complete workspace</a></li></ul>'
    msgs = [f.message for f in ft003(lesson(html), TREE, current=True)]
    assert msgs == ["complete workspace Workspaces/X/b-complete.fmw not found in FMEData"]


def test_ft003_ok_and_not_exercise():
    html = '<h2>Resources</h2><ul><li><a href="https://s3.amazonaws.com/FMEData/FMEData/Workspaces/X/a-complete.fmw">Complete workspace</a></li></ul>'
    assert ft003(lesson(html), TREE, current=True) == []
    assert ft003(lesson("<p>x</p>", "2026.2/adv/Course 2026.2/Intro/index.html"), TREE, current=True) == []


def test_ft003_not_parsed_is_notice():
    found = ft003(lesson("<h2>Introduction</h2>"), TREE, current=True)
    assert [(f.severity, f.message) for f in found] == [("notice", "lesson not parsed: no Resources section")]


def test_ft005_broken_only():
    html = ("https://example.com/gone https://support.safe.com/s/article/x "
            "http://localhost:8080/a https://example.com/ok")
    statuses = {"https://example.com/gone": 404, "https://support.safe.com/s/article/x": 403,
                "http://localhost:8080/a": None, "https://example.com/ok": 200}
    found = ft005(lesson(f"<p>{html}</p>"), statuses, CFG, current=True)
    assert [f.message for f in found] == ["https://example.com/gone returned 404"]


def test_ft_severity_by_currency():
    l = lesson(r"<p>C:\FMEData\Data\Gone.csv</p>")
    assert ft001(l, TREE, CFG, current=False)[0].severity == "notice"
    assert ft001(l, TREE, CFG, current=True)[0].severity == "warning"
