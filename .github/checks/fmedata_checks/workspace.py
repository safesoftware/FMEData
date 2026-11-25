"""Read what the checks need from an FME workspace (.fmw/.fmwt) file."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .refs import USER_PATH_RE, Ref, decode_fme, find_local_paths, find_s3_urls

_BUILD_RE = re.compile(r'LAST_SAVE_BUILD="FME\(R\)\s+([\d.]+)\s*\([^)]*Build\s+(\d+)')


@dataclass
class Workspace:
    path: str
    build: str | None
    build_num: int | None
    local_refs: list[Ref] = field(default_factory=list)
    s3_refs: list[Ref] = field(default_factory=list)
    header_user_paths: list[Ref] = field(default_factory=list)
    dataset_user_paths: list[Ref] = field(default_factory=list)


def _header_end(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if not line.startswith("#"):
            return i
    return len(lines)


def parse_workspace(path: str, text: str) -> Workspace:
    m = _BUILD_RE.search(text)
    lines = text.splitlines()
    end = _header_end(lines)
    header_users, dataset_users = [], []
    for n, line in enumerate(lines, start=1):
        decoded = decode_fme(line)
        for um in USER_PATH_RE.finditer(decoded):
            ref = Ref(n, um.group(0), "")
            # A plain "#" line in the header is the command-line comment FME writes, not a dataset.
            if n <= end and line.startswith("#") and not line.startswith("#!"):
                header_users.append(ref)
            else:
                dataset_users.append(ref)
    return Workspace(
        path=path,
        build=m.group(1) if m else None,
        build_num=int(m.group(2)) if m else None,
        local_refs=find_local_paths(text),
        s3_refs=find_s3_urls(text),
        header_user_paths=header_users,
        dataset_user_paths=dataset_users,
    )
