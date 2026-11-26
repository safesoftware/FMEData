"""Data/manifest.toml: where each data file comes from and its license (read by FD008)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field

from .tree import RepoTree

MANIFEST = "Data/manifest.toml"
SCOPE = "Data/"
_KEYS = {"source", "license", "url", "files"}


@dataclass(frozen=True)
class Entry:
    source: str
    license: str
    files: tuple[str, ...]
    line: int | None = None
    # Each pattern's line in the manifest, for pointing a finding at it.
    file_lines: dict[str, int | None] = field(default_factory=dict, compare=False)


def _regex(pattern: str) -> re.Pattern:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def matches(pattern: str, path: str) -> bool:
    """An exact path, or a glob: * and ? stay within one folder, ** spans folders. Case-sensitive, like S3."""
    return _regex(pattern).fullmatch(path) is not None


def data_files(tree: RepoTree) -> list[str]:
    return sorted(p for p in tree.all_files() if p.startswith(SCOPE) and p != MANIFEST)


def _line_after(lines: list[str], start: int, needle: str) -> int | None:
    for n in range(start, len(lines)):
        if needle in lines[n]:
            return n + 1
    return None


def load_manifest(text: str) -> tuple[list[Entry], list[tuple[int | None, str]]]:
    """The manifest's well-formed entries, and (line, message) for each problem. Raises on invalid TOML."""
    data = tomllib.loads(text)
    lines = text.splitlines()
    headers = [n for n, line in enumerate(lines) if re.match(r"\s*\[\[\s*entry\s*\]\]", line)]
    errors: list[tuple[int | None, str]] = [(None, f"unknown top-level key {k!r}; entries are [[entry]] tables")
                                            for k in data if k != "entry"]
    entries = []
    for i, raw in enumerate(data.get("entry", [])):
        start = headers[i] if i < len(headers) else 0
        line = start + 1 if i < len(headers) else None
        errors += [(line, f"unknown key {k!r}; an entry has source, license, files, and url") for k in raw if k not in _KEYS]
        source, files = raw.get("source"), raw.get("files")
        ok = True
        if not isinstance(source, str) or not source.strip():
            errors.append((line, "this entry needs a source"))
            ok = False
        if not isinstance(files, list) or not files or not all(isinstance(p, str) and p for p in files):
            errors.append((line, "files must be a list of paths or globs"))
            ok = False
        if ok:
            license_ = raw.get("license")
            entries.append(Entry(source.strip(), license_.strip() if isinstance(license_, str) else "",
                                 tuple(files), line,
                                 {p: _line_after(lines, start, f'"{p}"') or _line_after(lines, start, f"'{p}'")
                                  for p in files}))
    return entries, errors


def _folder(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) > 2 else parts[0]


def coverage(tree: RepoTree, entries: list[Entry]) -> dict[str, tuple[int, int]]:
    """For each folder under Data/: (files with a source and license, all files)."""
    complete = [_regex(p) for e in entries if e.license for p in e.files]
    counts: dict[str, list[int]] = {}
    for path in data_files(tree):
        c = counts.setdefault(_folder(path), [0, 0])
        c[1] += 1
        c[0] += any(rx.fullmatch(path) for rx in complete)
    return {k: (v[0], v[1]) for k, v in sorted(counts.items())}
