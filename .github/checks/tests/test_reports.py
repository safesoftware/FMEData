from datetime import datetime, timezone
from pathlib import Path

from fmedata_checks.lessons import lesson_index, parse_lesson, read_index
from fmedata_checks.model import Finding
from fmedata_checks.reports import build_reports, redact

USER = "C:" + "\\Users\\someone\\Desktop\\x.fmw"
GEN = datetime(2026, 11, 26, 2, 0, tzinfo=timezone.utc)


def lessons():
    return [
        parse_lesson("2026.2/adv/Course <script> 2026.2/Exercise_ A/index.html",
                     f"<p>https://example.com/gone {USER} C:\\FMEData\\Data\\x.shp</p>"),
    ]


def build(tmp_path: Path) -> Path:
    ls = lessons()
    findings = [
        Finding("FT005", ls[0].rel_html, None, "https://example.com/gone returned 404", "warning"),
        Finding("FD003", "Workspaces/a.fmw", 3, f"dataset path under {USER}", "error"),
        Finding("FD001", "Resources/X/a.fmw", 1, "Data/y.shp not found in FMEData", "notice"),
    ]
    statuses = {"https://example.com/gone": 404}
    build_reports(ls, findings, statuses, lesson_index(ls), tmp_path, GEN, fmetraining_sha="abc123",
                  exempt=["Resources/"])
    return tmp_path


def test_redact_user_paths():
    assert redact(USER) == "C:\\Users\\…\\Desktop\\x.fmw"


def test_reports_written(tmp_path: Path):
    out = build(tmp_path)
    assert {p.name for p in out.iterdir()} >= {"index.html", "broken-links.html", "findings.json"}


def test_reports_contain_no_user_names(tmp_path: Path):
    out = build(tmp_path)
    for p in out.iterdir():
        assert "someone" not in p.read_text(encoding="utf-8"), p.name


def test_findings_json_roundtrip(tmp_path: Path):
    out = build(tmp_path)
    idx, stale = read_index(str(out / "findings.json"), max_age_days=100000)
    assert idx == lesson_index(lessons()) and not stale


def test_html_escapes_content(tmp_path: Path):
    out = build(tmp_path)
    text = (out / "index.html").read_text(encoding="utf-8") + (out / "broken-links.html").read_text(encoding="utf-8")
    assert "<script> 2026.2" not in text and "&lt;script&gt;" in text


def test_broken_links_lists_url_and_status(tmp_path: Path):
    text = (build(tmp_path) / "broken-links.html").read_text(encoding="utf-8")
    assert "https://example.com/gone" in text and "404" in text


def test_index_separates_not_enforced(tmp_path: Path):
    text = (build(tmp_path) / "index.html").read_text(encoding="utf-8")
    assert "Not enforced" in text and "Resources/X/a.fmw" in text
