import html
import re
from datetime import datetime, timezone
from pathlib import Path

from fmedata_checks.model import CHECKS, Finding
from fmedata_checks.reports import build_reports

REPO = Path(__file__).resolve().parents[3]


def test_every_documented_check_has_a_name_and_summary():
    documented = set(re.findall(r"^### (F[DT]\d{3})$", (REPO / "CHECKS.md").read_text(encoding="utf-8"), re.M))
    assert documented == set(CHECKS)
    for check_id, (name, summary) in CHECKS.items():
        assert name and summary and len(summary) <= 90, check_id


def test_report_spells_out_every_check(tmp_path: Path):
    findings = [Finding("FD001", "Workspaces/a.fmw", 1, "Data/x.shp not found in FMEData", "warning")]
    build_reports([], findings, {}, {}, tmp_path, datetime.now(timezone.utc))
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    for check_id, (name, summary) in CHECKS.items():
        assert check_id in page and html.escape(name) in page and html.escape(summary) in page, check_id
    assert "Fails a pull request" in page
    assert page.count("Runs on pull requests only") == 2  # FD006 and FD010 never appear in the nightly counts


def test_lesson_checks_never_claim_to_fail_a_pull_request(tmp_path: Path):
    from fmedata_checks.model import Config
    build_reports([], [], {}, {}, tmp_path, datetime.now(timezone.utc), cfg=Config(enforce={"FD006", "FT005"}))
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    row = page[page.find("FT005"):page.find("</tr>", page.find("FT005"))]
    assert "Fails a pull request" not in row
