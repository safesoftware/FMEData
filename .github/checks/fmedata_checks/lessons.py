"""Read FME Academy lesson pages from the FMETraining archive.

The archive lays lessons out as <FME version>/<learning path>/<course>/<lesson>/index.html. The course
folder name ends with the course's own version ("Compare Workspaces 2025.1"), which can differ from the
archive's version folder.
"""

from __future__ import annotations

import fnmatch
import html as html_lib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator

from .refs import Ref, find_local_paths, find_s3_urls, find_web_urls

_VERSION_DIR = re.compile(r"^\d{4}\.\d+$")
_COURSE_VERSION = re.compile(r"^(.*?)\s+(\d{4}\.\d+)$")
_RESOURCES = re.compile(r"<h[1-6][^>]*>\s*Resources\s*</h[1-6]>(.*?)(?=<h[1-6][\s>]|\Z)", re.I | re.S)
_ANCHOR = re.compile(r"<a\b[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_TEXT_ITEM = re.compile(r"(Starting|Complete)\s+workspace\s*\|?\s*([^<]*)", re.I)


@dataclass
class Lesson:
    version: str
    learning_path: str
    course: str
    course_base: str
    course_version: str | None
    title: str
    rel_html: str
    is_exercise: bool
    parsed: bool
    starting: list[str] = field(default_factory=list)
    complete: list[str] = field(default_factory=list)
    local_refs: list[Ref] = field(default_factory=list)
    s3_refs: list[Ref] = field(default_factory=list)
    web_refs: list[Ref] = field(default_factory=list)
    has_step1: bool = False
    step1_mentions_start: bool = False
    step1_workspaces: list[str] = field(default_factory=list)
    # The page's words and link targets, lowercased, with / for \ (FT004 looks for data file names in it).
    text: str = ""


def _page_text(page: str) -> str:
    hrefs = " ".join(urllib.parse.unquote(m.group(1)) for m in _ANCHOR.finditer(page))
    words = html_lib.unescape(_TAG.sub(" ", page))
    return re.sub(r"\s+", " ", f"{words} {hrefs}").replace("\\", "/").lower()


_HEADING = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.I | re.S)
_STEP1 = re.compile(r"^(?:step\s*)?1(?:[).:]|\s|$)", re.I)
_MENTIONS_START = re.compile(r"starting\s+workspace|colleague.?s\s+workspace", re.I)


def _step1(page: str) -> tuple[bool, bool, list[str]]:
    heads = list(_HEADING.finditer(page))
    for i, m in enumerate(heads):
        title = html_lib.unescape(_TAG.sub("", m.group(2))).strip()
        if _STEP1.match(title):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(page)
            section = page[m.end():end]
            text = html_lib.unescape(_TAG.sub(" ", section))
            rels = [r.rel for r in find_local_paths(section) if r.rel.endswith((".fmw", ".fmwt"))]
            return True, bool(_MENTIONS_START.search(text)), list(dict.fromkeys(rels))
    return False, False, []


def _kind(label: str) -> str | None:
    low = _TAG.sub("", label).lower()
    if "workspace" not in low:
        return None
    if "complete" in low:
        return "complete"
    if "starting" in low or "start" in low:
        return "starting"
    return None


def _resources(section: str) -> tuple[list[str], list[str]]:
    starting, complete = [], []
    anchors = list(_ANCHOR.finditer(section))
    for i, m in enumerate(anchors):
        kind = _kind(m.group(2))
        if not kind:
            continue
        s3 = [r.rel for r in find_s3_urls(m.group(1)) if r.rel]
        if not s3:
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(section)
            s3 = [r.rel for r in find_local_paths(section[m.end():end])][:1]
        (complete if kind == "complete" else starting).extend(s3[:1])
    if not anchors or not (starting or complete):
        for m in _TEXT_ITEM.finditer(section):
            paths = [r.rel for r in find_local_paths(m.group(2))]
            if paths:
                (complete if m.group(1).lower() == "complete" else starting).append(paths[0])
    return starting, complete


def parse_lesson(rel_html: str, html: str) -> Lesson:
    parts = rel_html.replace("\\", "/").split("/")
    version, learning_path, course, title = parts[0], parts[1], parts[2], parts[3]
    m = _COURSE_VERSION.match(course)
    course_base, course_version = (m.group(1), m.group(2)) if m else (course, None)
    is_exercise = title.startswith("Exercise_")
    starting: list[str] = []
    complete: list[str] = []
    section = _RESOURCES.search(html)
    if section:
        starting, complete = _resources(section.group(1))
    # Newer exercises' titles don't start with "Exercise"; listing a complete workspace marks them too (FD004).
    has_step1, mentions_start, step1_ws = _step1(html) if is_exercise or complete else (False, False, [])
    return Lesson(
        has_step1=has_step1, step1_mentions_start=mentions_start, step1_workspaces=step1_ws,
        version=version, learning_path=learning_path, course=course, course_base=course_base,
        course_version=course_version, title=title, rel_html=rel_html, is_exercise=is_exercise,
        parsed=(not is_exercise) or section is not None,
        starting=starting, complete=complete,
        local_refs=find_local_paths(html), s3_refs=find_s3_urls(html), web_refs=find_web_urls(html),
        text=_page_text(html),
    )


def iter_lessons(root: Path, ignore_courses: list[str] | None = None) -> Iterator[Lesson]:
    """Lesson pages under a version folder, skipping courses whose name matches an ignore pattern."""
    root = Path(root)
    ignore = ignore_courses or []
    for page in sorted(root.glob("*/*/*/*/index.html")):
        rel = page.relative_to(root).as_posix()
        parts = rel.split("/")
        if not _VERSION_DIR.match(parts[0]) or any(fnmatch.fnmatchcase(parts[2], p) for p in ignore):
            continue
        yield parse_lesson(rel, page.read_text(encoding="utf-8", errors="replace"))


def ignored_courses(root: Path, ignore_courses: list[str]) -> list[str]:
    """Course folders (version/path/course) that match an ignore pattern: copies and test courses."""
    found = set()
    for page in Path(root).glob("*/*/*/*/index.html"):
        version, path, course = page.relative_to(root).as_posix().split("/")[:3]
        if _VERSION_DIR.match(version) and any(fnmatch.fnmatchcase(course, p) for p in ignore_courses):
            found.add(f"{version}/{path}/{course}")
    return sorted(found)


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in version.split("."))


def latest_versions(lessons: Iterable[Lesson]) -> dict[str, str]:
    latest: dict[str, str] = {}
    for lesson in lessons:
        v = lesson.course_version
        if v and (lesson.course_base not in latest or _key(v) > _key(latest[lesson.course_base])):
            latest[lesson.course_base] = v
    return latest


def is_current(lesson: Lesson, latest: dict[str, str]) -> bool:
    """A lesson is current when its course's name carries that course's newest version.

    A course's version comes from its name, as in Skilljar's tags, labels, and course names. Academy URLs
    carry a version only for archived courses, so versions are never read from URLs. A course whose name has
    no version is treated as archived: its findings are notices, and FD010 only warns about its links.
    """
    if lesson.course_version is None:
        return False
    return latest.get(lesson.course_base) == lesson.course_version


def previous_version(lesson: Lesson, lessons: Iterable[Lesson]) -> str | None:
    """The course's newest version before this lesson's, if the archive has one."""
    if not lesson.course_version:
        return None
    mine = _key(lesson.course_version)
    older = {l.course_version for l in lessons
             if l.course_base == lesson.course_base and l.course_version and _key(l.course_version) < mine}
    return max(older, key=_key) if older else None


def workspace_refs(lesson: Lesson) -> list[str]:
    """Every FMEData workspace a lesson links, in order, without repeats."""
    rels = [*lesson.starting, *lesson.complete, *(r.rel for r in [*lesson.local_refs, *lesson.s3_refs])]
    return list(dict.fromkeys(r for r in rels if r.endswith((".fmw", ".fmwt"))))


def lesson_label(lesson: Lesson) -> str:
    return f"{lesson.version} / {lesson.course} / {lesson.title}"


def lesson_index(lessons: Iterable[Lesson]) -> dict[str, list[str]]:
    """FMEData path -> the lessons that link it (by local path or main-branch S3 URL)."""
    idx: dict[str, set[str]] = {}
    for lesson in lessons:
        for ref in [*lesson.local_refs, *lesson.s3_refs]:
            if ref.rel:
                idx.setdefault(ref.rel, set()).add(lesson_label(lesson))
    return {rel: sorted(labels) for rel, labels in sorted(idx.items())}


def current_index(lessons: list[Lesson]) -> dict[str, list[str]]:
    """The lesson index restricted to lessons in each course's latest version."""
    latest = latest_versions(lessons)
    return lesson_index(l for l in lessons if is_current(l, latest))


def write_index(idx: dict[str, list[str]], path: Path) -> None:
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "lesson_index": idx}
    Path(path).write_text(json.dumps(payload, indent=1), encoding="utf-8")


def load_report(path_or_url: str) -> dict | None:
    """findings.json from a path or URL, or None when it's missing or unreadable."""
    try:
        if path_or_url.startswith(("http://", "https://")):
            with urllib.request.urlopen(path_or_url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        return json.loads(Path(path_or_url).read_text(encoding="utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None


def _stale(data: dict, max_age_days: int) -> bool:
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(data["generated_at"]) > timedelta(days=max_age_days)
    except (KeyError, ValueError, TypeError):
        return True


def read_index(path_or_url: "str | dict | None", max_age_days: int = 7, with_current: bool = False):
    """Read the lesson index from findings.json (a path, a URL, or a report already loaded).

    Returns (index, stale), or (index, current_index, stale) with with_current. stale is True when the file
    is missing, unreadable, or older than max_age_days. A file without a current index (from an older report)
    yields None for it, which FD010 treats as "every lesson is current".
    """
    data = load_report(path_or_url) if isinstance(path_or_url, str) else path_or_url
    if data is None:
        return ({}, None, True) if with_current else ({}, True)
    idx = data.get("lesson_index", {})
    stale = _stale(data, max_age_days)
    if with_current:
        return idx, data.get("current_index"), stale
    return idx, stale


@dataclass(frozen=True)
class Exercise:
    """What FD004 needs from an exercise lesson; the nightly report publishes these for pull requests."""
    label: str
    current: bool
    starting: tuple[str, ...]
    complete: tuple[str, ...]
    step1_start: bool


def exercises(lessons: Iterable[Lesson], latest: dict[str, str]) -> list[Exercise]:
    """Every lesson whose Resources lists a complete workspace (newer exercises' titles don't say "Exercise")."""
    return [Exercise(lesson_label(l), is_current(l, latest), tuple(l.starting), tuple(l.complete),
                     l.step1_mentions_start) for l in lessons if l.complete]


def exercise_json(ex: Exercise) -> dict:
    """One exercise for findings.json; empty lists and false flags are left out to keep the file small."""
    out: dict = {"lesson": ex.label, "current": ex.current}
    if ex.starting:
        out["starting"] = list(ex.starting)
    out["complete"] = list(ex.complete)
    if ex.step1_start:
        out["step1_start"] = True
    return out


def read_exercises(path_or_url: "str | dict | None", max_age_days: int = 7) -> tuple[list[Exercise] | None, bool]:
    """The exercises from findings.json, and whether the file is stale.

    None when the file is missing, unreadable, or from a report that predates the exercise list.
    """
    data = load_report(path_or_url) if isinstance(path_or_url, str) else path_or_url
    if data is None:
        return None, True
    if not isinstance(data.get("exercises"), list):
        return None, _stale(data, max_age_days)
    def paths(value) -> tuple[str, ...]:
        if not isinstance(value, list) or not all(isinstance(p, str) for p in value):
            raise TypeError("expected a list of paths")
        return tuple(value)
    try:
        found = [Exercise(str(e["lesson"]), bool(e.get("current")), paths(e.get("starting", [])),
                          paths(e["complete"]), bool(e.get("step1_start"))) for e in data["exercises"]]
    except (KeyError, TypeError, AttributeError):
        return None, _stale(data, max_age_days)
    return found, _stale(data, max_age_days)
