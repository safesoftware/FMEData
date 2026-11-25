from fmedata_checks.checks_fd import fd001, fd002, fd003
from fmedata_checks.model import Config
from fmedata_checks.tree import RepoTree
from fmedata_checks.workspace import parse_workspace

TREE = RepoTree.from_paths(["Data/Parks/Parks.shp", "Workspaces/X/a.fmw"])

WS = "\n".join([
    "#! <?xml version=\"1.0\" encoding=\"UTF-8\" ?>",
    "#! <WORKSPACE",
    r'#        "C:\Program Files\FME\fme.exe" C:\Users\jdoe\Documents\a.fmw',
    "#!   LAST_SAVE_BUILD=\"FME(R) 2026.2.0.0 (20260617 - Build 26333 - WIN64)\"",
    "#! />",
    "",
    r"DEFAULT_MACRO SourceDataset_SHAPEFILE C:\FMEData\Data\Parks\Parks.shp",
    r"DEFAULT_MACRO SourceDataset_CSV C:\FMEData\Data\Nope.csv",
    r"DEFAULT_MACRO SourceDataset_TIF C:\FMEData\data\parks\parks.shp",
    r"DEFAULT_MACRO DestDataset_GDB C:\FMEData\Output\Training\Vancouver.gdb",
    r"DEFAULT_MACRO SourceDataset_XLS C:\Users\jdoe\Desktop\in.xlsx",
    "DEFAULT_MACRO SourceDataset_GML https://s3.amazonaws.com/FMEData/FMEData/Data/Parks/Parks.shp",
    "DEFAULT_MACRO SourceDataset_ZIP https://s3.amazonaws.com/FMEData/Orthophotos.zip",
])


def cfg(**kw):
    return Config(**kw)


def ws():
    return parse_workspace("Workspaces/X/a.fmw", WS)


def test_parse_build():
    w = ws()
    assert w.build == "2026.2.0.0"
    assert w.build_num == 26333


def test_parse_build_missing():
    assert parse_workspace("a.fmw", "DEFAULT_MACRO X 1").build is None


def test_fd001_missing_and_case():
    msgs = [f.message for f in fd001(ws(), TREE, cfg())]
    assert len(msgs) == 2
    assert any("Data/Nope.csv" in m and "not found" in m for m in msgs)
    assert any("differs only in case from Data/Parks/Parks.shp" in m for m in msgs)


def test_fd001_ignores_output_folder():
    assert not any("Output/" in f.message for f in fd001(ws(), TREE, cfg()))


def test_fd001_allowlisted():
    found = fd001(ws(), TREE, cfg(allow_paths={"Data/Nope.csv": "hosted elsewhere"}))
    assert not any("Nope.csv" in f.message for f in found)


def test_fd001_reports_line_and_error():
    f = next(f for f in fd001(ws(), TREE, cfg()) if "Nope" in f.message)
    assert (f.line, f.severity, f.check_id) == (8, "error", "FD001")


def test_fd002_in_prefix_uses_tree_not_network():
    def fetch(url):
        raise AssertionError("network used")
    assert fd002(ws(), TREE, cfg(), fetch=None) == []
    w = parse_workspace("a.fmw", "X https://s3.amazonaws.com/FMEData/FMEData/Data/Parks/Parks.shp")
    assert fd002(w, TREE, cfg(), fetch=fetch) == []


def test_fd002_in_prefix_missing():
    w = parse_workspace("a.fmw", "X https://s3.amazonaws.com/FMEData/FMEData/Data/Gone.zip")
    assert [f.check_id for f in fd002(w, TREE, cfg(), fetch=None)] == ["FD002"]


def test_fd002_off_prefix_uses_fetch():
    found = fd002(ws(), TREE, cfg(), fetch=lambda url: 404)
    assert [f.message for f in found] == ["https://s3.amazonaws.com/FMEData/Orthophotos.zip returned 404"]


def test_fd003_dataset_vs_header():
    found = fd003(ws())
    assert sorted(f.severity for f in found) == ["error", "notice"]
    assert all("jdoe" not in f.message for f in found)
    assert all("C:\\Users\\…" in f.message for f in found)
