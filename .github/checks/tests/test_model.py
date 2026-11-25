from pathlib import Path

import pytest

from fmedata_checks.model import Config, Finding, annotation, effective, load_config


def cfg(**kw):
    base = dict(enforce={"FD006"}, allow_paths={}, allow_urls={}, bot_refusers=[],
                complete_suffixes=["-complete"], exempt={})
    base.update(kw)
    return Config(**base)


def test_annotation_format():
    f = Finding("FD001", "Workspaces/a.fmw", 12, r"C:\FMEData\Data\x.shp not found", "error")
    assert annotation(f) == (
        r"::error file=Workspaces/a.fmw,line=12::FD001 C:\FMEData\Data\x.shp not found"
        " (see CHECKS.md#fd001)"
    )


def test_annotation_no_line():
    f = Finding("FD001", "a.fmw", None, "msg", "warning")
    assert annotation(f) == "::warning file=a.fmw::FD001 msg (see CHECKS.md#fd001)"


def test_effective_downgrades_unenforced():
    f = Finding("FD001", "Workspaces/a.fmw", 1, "m", "error")
    assert effective(f, cfg()).severity == "warning"


def test_effective_keeps_enforced():
    f = Finding("FD001", "Workspaces/a.fmw", 1, "m", "error")
    assert effective(f, cfg(enforce={"FD001", "FD006"})).severity == "error"


def test_fd006_always_enforced(tmp_path: Path):
    p = tmp_path / "checks.toml"
    p.write_text("enforce = []\n", encoding="utf-8")
    assert "FD006" in load_config(p).enforce


def test_load_ignore_courses(tmp_path: Path):
    p = tmp_path / "checks.toml"
    p.write_text('ignore_courses = ["Clone of *"]\n', encoding="utf-8")
    assert load_config(p).ignore_courses == ["Clone of *"]


def test_allowlist_requires_reason(tmp_path: Path):
    p = tmp_path / "checks.toml"
    p.write_text('[allow.paths]\n"Data/x.shp" = ""\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(p)


def test_exempt_path_is_notice():
    c = cfg(enforce={"FD001", "FD006"}, exempt={"Resources/": "shared with other teams"})
    assert effective(Finding("FD001", "Resources/X/a.fmw", 1, "m", "error"), c).severity == "notice"
    assert effective(Finding("FD006", "Resources/X/a.fmw", 1, "m", "error"), c).severity == "error"
    assert effective(Finding("FD010", "Resources/X/a.fmw", None, "m", "error"), c).severity == "warning"
