import subprocess
from pathlib import Path

from fmedata_checks.refs import decode_fme, find_local_paths, find_s3_urls, find_web_urls
from fmedata_checks.tree import RepoTree

TREE = RepoTree.from_paths([
    "Data/Parks/Parks.shp",
    "Data/Parks/Parks.dbf",
    "Data/CommunityMapping/CommunityMap.gdb/a00000001.gdbtable",
    "Data/A B.zip",
])


def test_resolve_exact_case_missing():
    assert TREE.resolve("Data/Parks/Parks.shp") == "exact"
    assert TREE.resolve("data/parks/parks.shp") == "case"
    assert TREE.resolve("Data/Nope.shp") == "missing"


def test_resolve_gdb_directory():
    assert TREE.resolve("Data/CommunityMapping/CommunityMap.gdb") == "exact"
    assert TREE.resolve("Data/CommunityMapping/CommunityMap.gdb/") == "exact"


def test_resolve_glob():
    assert TREE.resolve("Data/Parks/*.shp") == "exact"
    assert TREE.resolve("Data/Parks/*.tif") == "missing"


def test_actual_path_for_case_mismatch():
    assert TREE.actual("data/parks/parks.shp") == "Data/Parks/Parks.shp"


def test_from_git_lists_tracked_files(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "Data").mkdir()
    (tmp_path / "Data" / "x.csv").write_text("a", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    assert RepoTree.from_git(tmp_path).resolve("Data/x.csv") == "exact"


def test_decode_fme():
    assert decode_fme("C:<backslash>FMEData<backslash>Data<backslash>My<space>File.shp") == r"C:\FMEData\Data\My File.shp"
    assert decode_fme("a<solidus>b<openparen>1<closeparen><at>") == "a/b(1)@"


def test_find_local_paths_escaped_and_plain():
    text = "x\nSRC C:<backslash>FMEData<backslash>Data<backslash>Parks<backslash>Parks.shp\n" \
           "y\n" r'<p>C:\FMEData\Data\Parks\Parks.shp</p>'
    refs = find_local_paths(text)
    assert [(r.line, r.rel) for r in refs] == [(2, "Data/Parks/Parks.shp"), (4, "Data/Parks/Parks.shp")]


def test_find_local_paths_forward_slashes_and_quotes():
    refs = find_local_paths('"C:/FMEData/Data/Parks/Parks.shp"')
    assert [r.rel for r in refs] == ["Data/Parks/Parks.shp"]


def test_find_local_paths_strips_trailing_markup():
    refs = find_local_paths(r"C:\FMEData\Data\x.shp</strong>")
    assert [r.rel for r in refs] == ["Data/x.shp"]


def test_find_local_paths_strips_macro_braces():
    refs = find_local_paths(r"$(SourceDataset){C:\FMEData\Data\Planning\PlanningRestrictions.gpkg}")
    assert [r.rel for r in refs] == ["Data/Planning/PlanningRestrictions.gpkg"]


def test_find_local_paths_keeps_spaces_inside_html_text():
    refs = find_local_paths(r"<li>C:\FMEData\Resources\FMEUC25\Getting Started\a.fmw</li>")
    assert [r.rel for r in refs] == ["Resources/FMEUC25/Getting Started/a.fmw"]


def test_find_s3_urls_comma_joined_and_encoded():
    text = 'href="https://s3.amazonaws.com/FMEData/FMEData/Data/A%20B.zip,' \
           'https://s3.amazonaws.com/FMEData/FMEData/Data/C.zip"'
    assert [r.rel for r in find_s3_urls(text)] == ["Data/A B.zip", "Data/C.zip"]


def test_find_s3_urls_strip_macro_brace():
    refs = find_s3_urls("$(X){https://s3.amazonaws.com/FMEData/FMEData/Data/Addresses.zip}")
    assert [r.rel for r in refs] == ["Data/Addresses.zip"]


def test_find_local_paths_stops_at_paren_then_prose():
    refs = find_local_paths(r"(C:\FMEData\Data\Culture\PublicArt.xlsx). The steps are the same")
    assert [r.rel for r in refs] == ["Data/Culture/PublicArt.xlsx"]


def test_find_s3_off_prefix():
    refs = find_s3_urls("see https://s3.amazonaws.com/FMEData/Orthophotos.zip now")
    assert [(r.raw, r.rel) for r in refs] == [("https://s3.amazonaws.com/FMEData/Orthophotos.zip", "")]


def test_find_s3_html_escaped_ampersand():
    refs = find_s3_urls('href="https://s3.amazonaws.com/FMEData/FMEData/Data/x.zip?a=1&amp;b=2"')
    assert [r.rel for r in refs] == ["Data/x.zip"]


def test_find_web_urls_excludes_fmedata_s3():
    text = "https://s3.amazonaws.com/FMEData/FMEData/Data/x.zip and https://support.safe.com/s/article/1."
    assert [r.raw for r in find_web_urls(text)] == ["https://support.safe.com/s/article/1"]
