"""An index of the files in FMEData, for resolving the paths workspaces and lessons use."""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path
from typing import Iterable, Literal

Resolution = Literal["exact", "case", "missing"]


class RepoTree:
    def __init__(self, files: Iterable[str]):
        self._files = {f.strip("/") for f in files}
        self._dirs: set[str] = set()
        for f in self._files:
            parts = f.split("/")
            for i in range(1, len(parts)):
                self._dirs.add("/".join(parts[:i]))
        self._lower = {p.lower(): p for p in self._files | self._dirs}

    @classmethod
    def from_paths(cls, paths: Iterable[str]) -> "RepoTree":
        return cls(paths)

    @classmethod
    def from_git(cls, repo: Path, ref: str | None = None) -> "RepoTree":
        cmd = ["git", "-C", str(repo), "-c", "core.quotepath=false"]
        cmd += ["ls-tree", "-r", "--name-only", ref] if ref else ["ls-files"]
        out = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        return cls(line for line in out.splitlines() if line)

    def all_files(self) -> set[str]:
        return set(self._files)

    def resolve(self, rel: str) -> Resolution:
        rel = rel.strip("/")
        if any(ch in rel for ch in "*?["):
            pattern = rel
            if any(fnmatch.fnmatchcase(p, pattern) for p in self._files | self._dirs):
                return "exact"
            low = pattern.lower()
            if any(fnmatch.fnmatchcase(p.lower(), low) for p in self._files | self._dirs):
                return "case"
            return "missing"
        if rel in self._files or rel in self._dirs:
            return "exact"
        if rel.lower() in self._lower:
            return "case"
        return "missing"

    def actual(self, rel: str) -> str | None:
        """The real spelling of a path that differs only in case."""
        return self._lower.get(rel.strip("/").lower())
