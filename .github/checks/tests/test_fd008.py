"""FD008: every data file under Data/ has a source and license in Data/manifest.toml."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from fmedata_checks.checks_fd import fd008
from fmedata_checks.manifest import MANIFEST, attribution, coverage, load_manifest, matches
from fmedata_checks.reports import build_reports
from fmedata_checks.tree import RepoTree

REPO = Path(__file__).resolve().parents[3]

TREE = RepoTree.from_paths([
    "Data/Parks/Parks.tab", "Data/Parks/Parks.dat",
    "Data/OpenStreetMap/highway.osm", "Data/OpenStreetMap/sub/amenity.osm",
    "Data/GPS/WalkingTrail.csv", "Data/GPS/ElectricCarTrack.json",
    MANIFEST, "Workspaces/a.fmw", "Resources/x.shp",
])

ENTRY = '''
[[entry]]
source = "{source}"
license = "{license}"
files = [{files}]
'''


def manifest(*entries: tuple[str, str, str]) -> str:
    return "".join(ENTRY.format(source=s, license=l, files=", ".join(f'"{p}"' for p in fs.split()))
                   for s, l, fs in entries)


def by_id(found):
    return [(f.path, f.line, f.message) for f in found]


def test_patterns_match_exact_paths_and_globs():
    assert matches("Data/GPS/WalkingTrail.csv", "Data/GPS/WalkingTrail.csv")
    assert not matches("Data/GPS/WalkingTrail.csv", "Data/GPS/walkingtrail.csv")  # case-sensitive, like S3
    assert matches("Data/GPS/*.csv", "Data/GPS/WalkingTrail.csv")
    assert not matches("Data/*.csv", "Data/GPS/WalkingTrail.csv")  # * stays within one folder
    assert matches("Data/OpenStreetMap/**", "Data/OpenStreetMap/sub/amenity.osm")
    assert matches("Data/**/amenity.osm", "Data/OpenStreetMap/sub/amenity.osm")
    assert matches("Data/**/highway.osm", "Data/highway.osm")  # ** matches zero folders too
    assert not matches("Data/OpenStreetMap/**", "Data/OpenStreetMapX/a.osm")
    assert matches("Data/[old]/a.shp", "Data/[old]/a.shp")  # brackets are literal


def test_file_covered_by_exact_path_has_no_finding():
    text = manifest(("A", "L", "Data/GPS/WalkingTrail.csv Data/GPS/ElectricCarTrack.json"),
                    ("B", "L", "Data/Parks/** Data/OpenStreetMap/**"))
    assert fd008(TREE, text) == []


def test_file_covered_by_glob_has_no_finding():
    text = manifest(("A", "L", "Data/**"))
    assert fd008(TREE, text) == []


def test_missing_files_are_reported_once_per_folder():
    text = manifest(("OSM", "L", "Data/OpenStreetMap/**"))
    found = fd008(TREE, text)
    assert all(f.check_id == "FD008" and f.severity == "warning" for f in found)
    assert [f.path for f in found] == ["Data/GPS/", "Data/Parks/"]
    assert "2 file(s) have no source or license" in found[0].message
    assert "ElectricCarTrack.json" in found[0].message and "WalkingTrail.csv" in found[0].message
    # Only Data/ is in scope, and the manifest needn't describe itself (no "Data/" finding above).
    assert not any(p in f.message for f in found for p in ("a.fmw", "x.shp"))


def test_entry_matching_nothing_is_stale():
    text = manifest(("A", "L", "Data/**"), ("Old", "L", "Data/Gone/** Data/GPS"))
    found = fd008(TREE, text)
    assert [(f.path, f.severity) for f in found] == [(MANIFEST, "warning"), (MANIFEST, "warning")]
    lines = text.splitlines()
    assert "Data/Gone/**" in lines[found[0].line - 1] and "matches no file" in found[0].message
    # A bare folder name matches no file; the message says how to cover a folder.
    assert "Data/GPS/**" in found[1].message


def test_entry_without_license_leaves_its_files_uncovered():
    text = manifest(("A", "L", "Data/Parks/** Data/OpenStreetMap/** Data/GPS/ElectricCarTrack.json"),
                    ("Trail maker", "", "Data/GPS/WalkingTrail.csv"))
    found = fd008(TREE, text)
    assert by_id(found) == [("Data/GPS/", None, "1 file(s) name a source (Trail maker) but no license: WalkingTrail.csv")]


def test_malformed_entries_are_reported_on_the_manifest():
    text = '[[entry]]\nsource = "A"\nlicence = "L"\nfiles = ["Data/**"]\n'
    found = fd008(TREE, text)
    assert (MANIFEST, 1) in [(f.path, f.line) for f in found]
    assert any("unknown key 'licence'" in f.message for f in found)
    found = fd008(TREE, "[[entry]]\nlicense = 'L'\nfiles = 'Data/**'\n")
    assert any("needs a source" in f.message for f in found)
    assert any("files must be a list" in f.message for f in found)


def test_missing_or_unreadable_manifest_is_one_finding():
    assert by_id(fd008(TREE, None)) == [(MANIFEST, None, f"{MANIFEST} is missing; every data file needs a source and license")]
    found = fd008(TREE, "[[entry]\n")
    assert len(found) == 1 and found[0].path == MANIFEST and "can't be read" in found[0].message


def test_coverage_counts_files_with_source_and_license_by_folder():
    entries, _ = load_manifest(manifest(("OSM", "L", "Data/OpenStreetMap/**"), ("T", "", "Data/GPS/WalkingTrail.csv")))
    assert coverage(TREE, entries) == {"Data/GPS": (0, 2), "Data/OpenStreetMap": (2, 2), "Data/Parks": (0, 2)}


def test_report_shows_attribution_coverage(tmp_path: Path):
    build_reports([], [], {}, {}, tmp_path, datetime.now(timezone.utc),
                  attribution={"Data/GPS": (1, 2), "Data/Parks": (0, 3)})
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Data attribution" in page and "Data/GPS" in page and "1 of 5" in page
    data = json.loads((tmp_path / "findings.json").read_text(encoding="utf-8"))
    assert data["attribution_coverage"] == {"Data/GPS": [1, 2], "Data/Parks": [0, 3]}


def test_cli_lessons_reports_fd008(tmp_path: Path):
    from fmedata_checks.__main__ import main
    repo = tmp_path / "repo"
    (repo / "Data" / "GPS").mkdir(parents=True)
    (repo / "Data" / "GPS" / "a.csv").write_text("1", encoding="utf-8")
    (repo / "Data" / "manifest.toml").write_text(manifest(("A", "L", "Data/Old/**")), encoding="utf-8")
    for args in (["init", "-q"], ["add", "."]):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    (tmp_path / "archive").mkdir()
    cfg = tmp_path / "checks.toml"
    cfg.write_text("enforce = []\n", encoding="utf-8")
    main(["lessons", "--repo", str(repo), "--fmetraining", str(tmp_path / "archive"), "--out", str(tmp_path / "out"),
          "--no-network", "--config", str(cfg)])
    data = json.loads((tmp_path / "out" / "findings.json").read_text(encoding="utf-8"))
    assert sorted(f["path"] for f in data["findings"] if f["check_id"] == "FD008") == ["Data/GPS/", MANIFEST]
    assert data["attribution_coverage"] == {"Data/GPS": [0, 1]}


def test_shipped_manifest_reads_cleanly_and_has_no_stale_entries():
    text = (REPO / MANIFEST).read_text(encoding="utf-8")
    entries, errors = load_manifest(text)
    assert entries and errors == []
    stale = [f for f in fd008(RepoTree.from_git(REPO), text) if f.path == MANIFEST]
    assert stale == []


def test_shipped_folder_zips_credit_every_source_inside_them():
    # A zip member counts when it mirrors a file in the repo (Data/Addresses.zip's Addresses/x is Data/Addresses/x).
    # Inner zips are repo files too, so each is checked as its own zip. CI's sparse checkout has no zips.
    import zipfile
    entries, _ = load_manifest((REPO / MANIFEST).read_text(encoding="utf-8"))
    tree = RepoTree.from_git(REPO)
    files = tree.all_files()
    zips = sorted(p for p in files if p.startswith("Data/") and p.endswith(".zip") and (REPO / p).is_file())
    if not zips:
        pytest.skip("the data zips aren't checked out")
    for z in zips:
        parent = z.rsplit("/", 1)[0]
        with zipfile.ZipFile(REPO / z) as zf:
            members = [f"{parent}/{n}" for n in zf.namelist() if f"{parent}/{n}" in files]
        inside = {(e.source, e.license) for m in members for e in attribution(m, entries)}
        assert inside <= {(e.source, e.license) for e in attribution(z, entries)}, z


def test_shipped_city_entry_matches_the_default():
    entries, _ = load_manifest((REPO / MANIFEST).read_text(encoding="utf-8"))
    [default] = [e for e in entries if e.default]
    city = [e for e in entries if not e.default and e.source == default.source]
    assert city and all(e.license == default.license for e in city)


DEFAULT = '[default]\nsource = "City"\nlicense = "City license"\n'


def test_default_covers_files_no_entry_matches():
    entries, errors = load_manifest(DEFAULT + manifest(("OSM", "L", "Data/OpenStreetMap/**")))
    assert errors == []
    assert fd008(TREE, DEFAULT) == []
    assert coverage(TREE, entries) == {"Data/GPS": (2, 2), "Data/OpenStreetMap": (2, 2), "Data/Parks": (2, 2)}


def test_specific_entry_overrides_the_default():
    # A matching entry without a license isn't filled in from the default.
    text = DEFAULT + manifest(("Trail maker", "", "Data/GPS/WalkingTrail.csv"))
    found = fd008(TREE, text)
    assert by_id(found) == [("Data/GPS/", None, "1 file(s) name a source (Trail maker) but no license: WalkingTrail.csv")]
    entries, _ = load_manifest(text)
    assert coverage(TREE, entries)["Data/GPS"] == (1, 2)
    assert [e.source for e in attribution("Data/GPS/WalkingTrail.csv", entries)] == ["Trail maker"]
    assert [e.source for e in attribution("Data/Parks/Parks.tab", entries)] == ["City"]


def test_default_needs_source_and_license_and_no_files():
    found = fd008(TREE, '[default]\nsource = "City"\nfiles = ["Data/**"]\n')
    messages = [f.message for f in found if f.path == MANIFEST]
    assert any("default needs a license" in m for m in messages)
    assert any("unknown key 'files'" in m for m in messages)
    assert all(f.line == 1 for f in found if f.path == MANIFEST)


@pytest.mark.parametrize("text", [
    '[entry]\nsource = "A"\nfiles = ["Data/**"]\n',
    'entry = "x"\n',
    'entry = [1]\n',
])
def test_wrong_shape_is_a_finding_not_a_crash(text):
    found = fd008(RepoTree.from_paths(["Data/a.csv"]), text)
    assert any("entry" in f.message for f in found)


def test_a_license_that_is_not_text_is_reported_at_its_entry():
    text = '[[entry]]\nsource = "A"\nlicense = 5\nfiles = ["Data/**"]\n'
    found = fd008(RepoTree.from_paths(["Data/a.csv"]), text)
    assert any(f.line == 1 and "license must be text" in f.message for f in found)


def test_every_matching_entry_needs_a_license():
    text = ('[[entry]]\nsource = "A"\nlicense = "L"\nfiles = ["Data/a.csv"]\n'
            '[[entry]]\nsource = "B"\nfiles = ["Data/*.csv"]\n')
    tree = RepoTree.from_paths(["Data/a.csv"])
    found = fd008(tree, text)
    assert any("(B) but no license" in f.message for f in found)
    assert coverage(tree, load_manifest(text)[0]) == {"Data": (0, 1)}


def test_entries_get_no_line_when_headers_do_not_line_up():
    # a "[[entry]]" line inside a multi-line string is not a header; no line beats a wrong one
    text = '[[entry]]\nsource = """\n[[entry]]\n"""\nlicense = "L"\nfiles = ["Data/**"]\n'
    entries, errors = load_manifest(text)
    assert errors == [] and [e.line for e in entries] == [None]
