"""Read FME Academy lesson pages from the FMETraining archive.

The archive lays lessons out as <FME version>/<learning path>/<course>/<lesson>/index.html. The course
folder name ends with the course's own version ("Compare Workspaces 2025.1"), which can differ from the
archive's version folder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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
    return Lesson(
        version=version, learning_path=learning_path, course=course, course_base=course_base,
        course_version=course_version, title=title, rel_html=rel_html, is_exercise=is_exercise,
        parsed=(not is_exercise) or section is not None,
        starting=starting, complete=complete,
        local_refs=find_local_paths(html), s3_refs=find_s3_urls(html), web_refs=find_web_urls(html),
    )


def iter_lessons(root: Path) -> Iterator[Lesson]:
    root = Path(root)
    for page in sorted(root.glob("*/*/*/*/index.html")):
        rel = page.relative_to(root).as_posix()
        if not _VERSION_DIR.match(rel.split("/", 1)[0]):
            continue
        yield parse_lesson(rel, page.read_text(encoding="utf-8", errors="replace"))


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
    if lesson.course_version is None:
        return True
    return latest.get(lesson.course_base) == lesson.course_version

