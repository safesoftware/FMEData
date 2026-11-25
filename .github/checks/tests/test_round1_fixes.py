"""Regression tests for PR #10 review round 1."""

import http.client
import urllib.request

from fmedata_checks import links
from fmedata_checks.checks_fd import fd006, fd010
from fmedata_checks.gitdiff import Change
from fmedata_checks.lessons import is_current, latest_versions, parse_lesson
from fmedata_checks.refs import redact


def test_http_status_survives_malformed_reply(monkeypatch):
    def broken(*args, **kwargs):
        raise http.client.BadStatusLine("garbage")
    monkeypatch.setattr(urllib.request, "urlopen", broken)
    assert links.http_status("https://bad.example/x") is None


def test_fd010_matches_case_and_globs():
    idx = {"data/parks/parks.shp": ["2026.2 / C 2026.2 / L"], "Data/Roads/*.shp": ["2026.2 / C 2026.2 / M"]}
    found = fd010([Change("D", "Data/Parks/Parks.shp", None), Change("D", "Data/Roads/Main.shp", None)],
                  idx, stale=False, current=idx)
    assert sorted(f.path for f in found if f.severity == "error") == ["Data/Parks/Parks.shp", "Data/Roads/Main.shp"]


def test_unversioned_course_current_only_in_newest_archive_version():
    old = parse_lesson("2022.0/p/Getting Started/L/index.html", "")
    new = parse_lesson("2025.1/p/Getting Started/L/index.html", "")
    latest = latest_versions([old, new])
    assert not is_current(old, latest) and is_current(new, latest)


def test_fd006_user_folder_any_case_and_at_line_end():
    lower = "c:" + "\\users\\jsmith\\Desktop\\a.csv"
    at_end = "path C:" + "\\Users\\jsmith"
    assert len(fd006("notes.txt", [(1, lower)])) == 1
    assert len(fd006("notes.txt", [(1, at_end)])) == 1
    assert "jsmith" not in redact(lower) and "jsmith" not in redact(at_end)


def test_fd006_email_domain_matched_exactly():
    assert len(fd006("notes.txt", [(1, "someone" + "@" + "notexample.com")])) == 1
    assert fd006("notes.txt", [(1, "someone" + "@" + "mail.example.com")]) == []
