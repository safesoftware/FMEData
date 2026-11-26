"""A C:\\FMEData path written inside a sentence ends where the path ends, not at the end of the sentence.

Each case is taken from a current lesson in the 2026-11 archive, where the prose after the path used to be read as
part of it and produced a false FT001 warning.
"""

import pytest

from fmedata_checks.checks_ft import ft001
from fmedata_checks.lessons import parse_lesson
from fmedata_checks.model import Config
from fmedata_checks.refs import find_local_paths
from fmedata_checks.tree import RepoTree

TREE = RepoTree.from_paths([
    "Data/Engineering/BuildingFootprints/BuildingFootprints.shp",
    "Data/Orthophotos/tile1.tif",
    "Resources/DigitalPlanSubmission/plan.dwg",
    "Output/readme.txt",
    "Workspaces/Deploy/import-projects--starting-project.fsproject",
    "Resources/FMEUC25/Dynamic Workflows Training/Module 5/a.fmw",
])
REL = "2026.2/adv/Course 2026.2/Exercise_ E/index.html"


def rels(text):
    return [r.rel for r in find_local_paths(text)]


@pytest.mark.parametrize("text, expected", [
    # a closing parenthesis with no opening one inside the path ends it
    (r"(C:\FMEData\Data\Engineering\BuildingFootprints) of the Shapefile datasets to FME Flow",
     "Data/Engineering/BuildingFootprints"),
    (r"project (C:\FMEData\Workspaces\Deploy\import-projects--starting-project.fsproject) to the",
     "Workspaces/Deploy/import-projects--starting-project.fsproject"),
    # a file name followed by a full stop and the next sentence
    (r"Open C:\FMEData\Output\mcp_output.json. This JSON file is written by the MCP writer",
     "Output/mcp_output.json"),
    # a folder followed by a full stop and the next sentence
    (r"Browse to C:\FMEData\Output. Open the file", "Output"),
    # a separator followed by a space ends the path
    (r"Copy C:\FMEData\Resources\DigitalPlanSubmission\ into the folder", "Resources/DigitalPlanSubmission"),
])
def test_prose_after_a_path_is_not_part_of_it(text, expected):
    assert rels(text) == [expected]


@pytest.mark.parametrize("text, expected", [
    (r"C:\FMEData\Resources\FMEUC25\Dynamic Workflows Training\Module 5\a.fmw",
     "Resources/FMEUC25/Dynamic Workflows Training/Module 5/a.fmw"),
    (r"C:\FMEData\Data\Parks\Parks (copy).shp", "Data/Parks/Parks (copy).shp"),
    (r"C:\FMEData\Data\x.shp.xml", "Data/x.shp.xml"),
    # a numbered folder ("3. Make a Workspace Endpoint") is path, not a sentence break, because more path follows
    (r"C:\FMEData\Resources\FMEUC25\Data Virtualization\3. Make a Workspace Endpoint\a.fmw",
     "Resources/FMEUC25/Data Virtualization/3. Make a Workspace Endpoint/a.fmw"),
])
def test_real_paths_with_spaces_and_parentheses_are_kept(text, expected):
    assert rels(text) == [expected]


def test_ft001_accepts_a_folder_followed_by_words():
    """'C:\\FMEData\\Data\\Orthophotos is faster' names the Orthophotos folder; only the tree can tell where it ends."""
    lesson = parse_lesson(REL, r"<p>Reading C:\FMEData\Data\Orthophotos is faster than reading the .zip</p>")
    assert ft001(lesson, TREE, Config(), current=True) == []


def test_ft001_still_reports_a_missing_path_followed_by_words():
    lesson = parse_lesson(REL, r"<p>Reading C:\FMEData\Data\Nowhere is faster than reading the .zip</p>")
    found = ft001(lesson, TREE, Config(), current=True)
    assert len(found) == 1 and "Data/Nowhere is faster than reading the .zip" in found[0].message


@pytest.mark.parametrize("text, expected", [
    # a closing bracket that belongs to the URL is kept
    ('<a href="https://en.wikipedia.org/wiki/Battleship_(game)">', "https://en.wikipedia.org/wiki/Battleship_(game)"),
    ("see https://en.wikipedia.org/wiki/Glob_(programming).", "https://en.wikipedia.org/wiki/Glob_(programming)"),
    # a closing bracket that belongs to the sentence is not
    ("(see https://example.com/page)", "https://example.com/page"),
])
def test_url_keeps_its_own_closing_bracket(text, expected):
    from fmedata_checks.refs import find_web_urls
    assert [r.raw for r in find_web_urls(text)] == [expected]


def test_a_url_later_in_the_sentence_is_not_more_path():
    assert rels(r"Open C:\FMEData\Output\a.json. See https://docs.safe.com/x") == ["Output/a.json"]
    assert rels(r"Browse to C:\FMEData\Output. See https://docs.safe.com/x") == ["Output"]


@pytest.mark.parametrize("text, expected", [
    (r"C:\FMEData\Data\St. Louis.shp", "Data/St. Louis.shp"),
    (r"(C:\FMEData\Data\Parks (old)\a.shp)", "Data/Parks (old)/a.shp"),
])
def test_workspace_paths_keep_the_plain_rule(text, expected):
    # workspaces hold paths, not prose: the sentence-end rules apply only to lessons
    assert [r.rel for r in find_local_paths(text, prose=False)] == [expected]


def test_trimmed_candidate_drops_a_question_mark_rather_than_globbing():
    lesson = parse_lesson(REL, r"<p>Go to C:\FMEData\Data\Orthophotos? Yes</p>")
    assert ft001(lesson, TREE, Config(), current=True) == []
