"""What a pull request changes, read from git."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Change:
    status: Literal["A", "M", "D", "R"]
    path: str
    old_path: str | None


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=false", *args],
                          check=True, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def changed_files(repo: Path, base: str) -> list[Change]:
    out = _git(repo, "diff", "--name-status", "-M", f"{base}...HEAD")
    changes = []
    for line in out.splitlines():
        parts = line.split("\t")
        code = parts[0][0]
        if code == "R":
            changes.append(Change("R", parts[2], parts[1]))
        elif code in "AMD":
            changes.append(Change(code, parts[1], None))  # type: ignore[arg-type]
        else:  # copies and type changes read as modifications
            changes.append(Change("M", parts[-1], None))
    return changes


_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def added_lines(repo: Path, base: str, path: str, old_path: str | None = None) -> list[tuple[int, str]]:
    """Lines the change adds to path. Pass old_path for a rename, so unchanged lines don't count as added."""
    paths = [old_path, path] if old_path else [path]
    out = _git(repo, "diff", "-U0", "-M", f"{base}...HEAD", "--", *paths)
    lines, n, in_hunk = [], 0, False
    for line in out.splitlines():
        m = _HUNK.match(line)
        if m:
            n, in_hunk = int(m.group(1)), True
            continue
        if line.startswith("diff --git"):
            in_hunk = False
        if in_hunk and line.startswith("+"):
            lines.append((n, line[1:]))
            n += 1
    return lines
