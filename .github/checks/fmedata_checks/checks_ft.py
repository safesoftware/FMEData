"""Checks on FME Academy lesson pages against FMEData (FT = FMETraining).

Lessons are fixed in Skilljar, not here, so these findings never fail a pull request. A lesson in a course's
latest version gets warnings; older versions get notices.
"""

from __future__ import annotations

from .checks_fd import OUTPUT_PREFIX, _resolution_message
from .lessons import Lesson, workspace_refs
from .links import classify_url
from .model import Config, Finding, Severity
from .tree import RepoTree
from .workspace import Workspace


def _sev(current: bool) -> Severity:
    return "warning" if current else "notice"


def ft001(lesson: Lesson, tree: RepoTree, cfg: Config, current: bool) -> list[Finding]:
    """C:\\FMEData paths in a lesson resolve to files in FMEData."""
    found, seen = [], set()
    for r in lesson.local_refs:
        if r.rel in seen or r.rel.startswith(OUTPUT_PREFIX) or r.rel in cfg.allow_paths:
            continue
        seen.add(r.rel)
        msg = _resolution_message(r.rel, tree, r.rel)
        if msg:
            found.append(Finding("FT001", lesson.rel_html, None, msg, _sev(current)))
    return found


def ft002(lesson: Lesson, tree: RepoTree, cfg: Config, statuses: dict[str, int | None],
          current: bool) -> list[Finding]:
    """FMEData S3 links in a lesson resolve: main-branch ones against the tree, others by their HTTP status."""
    found, seen = [], set()
    for r in lesson.s3_refs:
        if r.raw in seen or r.raw in cfg.allow_urls:
            continue
        seen.add(r.raw)
        if r.rel:
            msg = _resolution_message(r.rel, tree, r.raw)
        else:
            status = statuses.get(r.raw)
            kind = classify_url(r.raw, status, cfg)
            msg = None if kind == "ok" or r.raw not in statuses else f"{r.raw} returned {status or 'no response'}"
        if msg:
            found.append(Finding("FT002", lesson.rel_html, None, msg, _sev(current)))
    return found


def ft003(lesson: Lesson, tree: RepoTree, current: bool) -> list[Finding]:
    """An exercise lists its complete workspace (and starting one, if any), and they exist."""
    if not lesson.is_exercise:
        return []
    if not lesson.parsed:
        return [Finding("FT003", lesson.rel_html, None, "lesson not parsed: no Resources section", "notice")]
    found = []
    if not lesson.complete:
        found.append(Finding("FT003", lesson.rel_html, None, "no complete workspace listed in Resources", _sev(current)))
    for kind, rels in (("starting", lesson.starting), ("complete", lesson.complete)):
        for rel in rels:
            if tree.resolve(rel) == "missing":
                found.append(Finding("FT003", lesson.rel_html, None,
                                     f"{kind} workspace {rel} not found in FMEData", _sev(current)))
    return found


def _named(rel: str, lesson: Lesson, links: set[str]) -> bool:
    """The lesson names a data file: by path or link, by file name, or by the zip or folder it's shipped as.

    A file in a folder is named by the folder's zip (Data/Orthophotos/02-03-HI.tif by Orthophotos.zip); a file in a
    geodatabase by the .gdb or its zip; a zip by its name without .zip (CommunityMap.gdb.zip by CommunityMap.gdb)
    or by a path into its folder (Data/Parks.zip by C:\\FMEData\\Data\\Parks\\Parks.tab).
    """
    low = rel.lower()
    parts = low.split("/")
    name = parts[-1]
    text = lesson.text
    if low in links or name in text:
        return True
    if name.endswith(".zip") and (name[:-4] in text or any(l.startswith(low[:-4] + "/") for l in links)):
        return True
    for folder in parts[1:-1]:
        if folder + ".zip" in text or (folder.endswith(".gdb") and folder in text):
            return True
    return False


def ft004(lesson: Lesson, workspaces_by_rel: dict[str, Workspace], current: bool) -> list[Finding]:
    """An exercise in a course's latest version names every data file its complete workspace reads.

    An exercise is any lesson whose Resources lists a complete workspace (newer exercises' titles don't start
    with "Exercise"). Paths under Output/ are destinations, and other workspaces aren't data.
    """
    if not (current and lesson.complete):
        return []
    links = {r.rel.lower() for r in [*lesson.local_refs, *lesson.s3_refs] if r.rel}
    start_reads = {r.rel for s in lesson.starting if s in workspaces_by_rel
                   for r in [*workspaces_by_rel[s].local_refs, *workspaces_by_rel[s].s3_refs]}
    found, seen = [], set()
    for complete in lesson.complete:
        ws = workspaces_by_rel.get(complete)
        if ws is None:
            continue
        for r in [*ws.local_refs, *ws.s3_refs]:
            rel = r.rel
            if (not rel or rel in seen or rel == "Output" or rel.startswith(OUTPUT_PREFIX)
                    or rel.endswith((".fmw", ".fmwt")) or _named(rel, lesson, links)):
                continue
            seen.add(rel)
            note = "; the starting workspace already reads it" if rel in start_reads else ""
            found.append(Finding("FT004", lesson.rel_html, None,
                                 f"{complete} reads {rel}, but the lesson doesn't name it{note}. "
                                 "List it under Resources", "warning"))
    return found


def fme_version(build: str | None) -> tuple[int, int] | None:
    if not build:
        return None
    parts = build.split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return None


def _course_key(version: str) -> tuple[int, int]:
    year, minor = version.split(".")[:2]
    return int(year), int(minor)


def ft006(lesson: Lesson, workspaces_by_rel: dict[str, Workspace], current: bool,
          previous_version: str | None) -> list[Finding]:
    """A linked workspace opens in the FME version the course names, and has been updated since the last version."""
    if not lesson.course_version:
        return []
    course = _course_key(lesson.course_version)
    found = []
    for rel in workspace_refs(lesson):
        ws = workspaces_by_rel.get(rel)
        saved = fme_version(ws.build) if ws else None
        if saved is None:
            continue
        shown = f"{saved[0]}.{saved[1]}"
        if saved > course:
            found.append(Finding("FT006", lesson.rel_html, None,
                                 f"{rel} was saved in FME {shown}, newer than the course's FME "
                                 f"{lesson.course_version}; learners on {lesson.course_version} can't open it",
                                 _sev(current)))
        elif previous_version and saved < _course_key(previous_version):
            found.append(Finding("FT006", lesson.rel_html, None,
                                 f"{rel} not updated since FME {shown} (the course's previous version is "
                                 f"{previous_version})", "notice"))
    return found


def is_legacy(rel: str) -> bool:
    return rel.rsplit("/", 1)[-1].startswith("exercise-")


def ft007(lesson: Lesson, current: bool) -> list[Finding]:
    """A lesson still links a workspace with the legacy exercise- prefix, which is being phased out."""
    return [Finding("FT007", lesson.rel_html, None,
                    f"links legacy workspace name {rel}; the exercise- prefix is being phased out", _sev(current))
            for rel in workspace_refs(lesson) if is_legacy(rel)]


def ft008(lesson: Lesson, current: bool) -> list[Finding]:
    """When an exercise starts from a workspace, Step 1 gives its C:\\FMEData path and Resources lists it."""
    if not (lesson.is_exercise and lesson.parsed and lesson.has_step1):
        return []
    expected = bool(lesson.starting) or lesson.step1_mentions_start or bool(lesson.step1_workspaces)
    if not expected:
        return []
    msgs = []
    if not lesson.starting:
        msgs.append("Step 1 opens a starting workspace, but Resources doesn't list one")
    if not lesson.step1_workspaces:
        msgs.append("Step 1 opens the starting workspace but doesn't give its C:\\FMEData path")
    elif lesson.starting and not set(lesson.step1_workspaces) & set(lesson.starting):
        msgs.append(f"Step 1 opens {lesson.step1_workspaces[0]}, but Resources lists {lesson.starting[0]}")
    return [Finding("FT008", lesson.rel_html, None, m, _sev(current)) for m in msgs]


def ft009(course_folders: list[str]) -> list[Finding]:
    """Skilljar copies and test courses don't belong in the lesson archive."""
    return [Finding("FT009", c, None,
                    "course copy or test course in the lesson archive; remove it from Skilljar or the S3 export",
                    "warning") for c in course_folders]


def ft005(lesson: Lesson, statuses: dict[str, int | None], cfg: Config, current: bool) -> list[Finding]:
    """Web links in a lesson answer. Bot-refusing hosts and localhost are reported separately, not as broken."""
    found, seen = [], set()
    for r in lesson.web_refs:
        if r.raw in seen or r.raw in cfg.allow_urls or r.raw not in statuses:
            continue
        seen.add(r.raw)
        if classify_url(r.raw, statuses[r.raw], cfg) == "broken":
            found.append(Finding("FT005", lesson.rel_html, None,
                                 f"{r.raw} returned {statuses[r.raw]}", _sev(current)))
    return found
