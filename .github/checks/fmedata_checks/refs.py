"""Find FMEData paths and URLs in workspace and lesson text."""

from __future__ import annotations

import html
import re
import urllib.parse
from dataclasses import dataclass

# FME writes some characters in workspace files as named tokens.
_FME_TOKENS = {
    "backslash": "\\", "solidus": "/", "space": " ", "openparen": "(", "closeparen": ")",
    "at": "@", "quote": '"', "apos": "'", "comma": ",", "semicolon": ";", "lt": "<", "gt": ">",
    "amp": "&", "openbracket": "[", "closebracket": "]", "opencurly": "{", "closecurly": "}",
}
_FME_TOKEN_RE = re.compile(r"<(" + "|".join(_FME_TOKENS) + r"|u[0-9a-fA-F]{4})>")

S3_FMEDATA = "s3.amazonaws.com/FMEData/"
S3_MAIN_PREFIX = "s3.amazonaws.com/FMEData/FMEData/"

_LOCAL_RE = re.compile(r"[Cc]:[\\/]FMEData[\\/]([^\"'<>\r\n,;|\t{}]+)")
_URL_RE = re.compile(r"https?://[^\s\"'<>{}]+")
_EXT_THEN_SPACE = re.compile(r"^(.*?\.[A-Za-z0-9]{1,8})(?=[.,;:!?]?(?:[\s)\]]|$))")
# Workspaces hold paths, not prose, so they keep the plain rule: a file name ends at whitespace or a bracket.
_EXT_THEN_SPACE_WS = re.compile(r"^(.*?\.[A-Za-z0-9]{1,8})(?=[\s)\]])")
_URL_IN_REST = re.compile(r"https?://\S*")
# A full stop and a space, or a separator and a space, start the next words of the sentence, not more path.
_SENTENCE_BREAK = re.compile(r"\.\s|[\\/]\s")
_TRAILING = ".,;:)]"


def _cut_unmatched_paren(path: str) -> str:
    """'...\\BuildingFootprints) of the data': a ')' with no '(' before it in the path closes the sentence's bracket."""
    depth = 0
    for i, ch in enumerate(path):
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                return path[:i]
            depth -= 1
    return path


USER_PATH_RE = re.compile(r"(c:[\\/]users[\\/])([^\s\\/\"'<>…][^\\/\"'<>\r\n]*?)(?=[\\/\"'<>]|$)", re.I)


def redact(text: str) -> str:
    """Hide the user name in C:\\Users\\<name>\\... paths."""
    return USER_PATH_RE.sub(lambda m: m.group(1) + "…", text)


@dataclass(frozen=True)
class Ref:
    line: int
    raw: str
    rel: str


def decode_fme(text: str) -> str:
    def sub(m: re.Match) -> str:
        tok = m.group(1)
        if tok.startswith("u") and len(tok) == 5 and tok not in _FME_TOKENS:
            return chr(int(tok[1:], 16))
        return _FME_TOKENS[tok]
    return _FME_TOKEN_RE.sub(sub, text)


def _lines(text: str):
    for n, line in enumerate(text.splitlines(), start=1):
        yield n, html.unescape(decode_fme(line))


def _more_path(rest: str) -> bool:
    """True when a separator follows, ignoring any URL later in the sentence ("... a.json. See https://...")."""
    rest = _URL_IN_REST.sub("", rest)
    return "\\" in rest or "/" in rest


def _clean_local(captured: str, prose: bool = True) -> str:
    path = captured.strip()
    if prose:
        path = _cut_unmatched_paren(path)
        for brk in _SENTENCE_BREAK.finditer(path):
            # "3. Make a Workspace Endpoint\a.fmw" is a numbered folder: more path follows, so it isn't a break.
            if not _more_path(path[brk.end():]):
                path = path[:brk.start() + 1]
                break
        # Prose after a path ("...\Parks.shp in Workbench"): stop after the first file name with an extension.
        m = _EXT_THEN_SPACE.match(path)
        if m and not _more_path(path[m.end():]):
            path = m.group(1)
    else:
        m = _EXT_THEN_SPACE_WS.match(path)
        if m and "\\" not in path[m.end():] and "/" not in path[m.end():]:
            path = m.group(1)
    path = path.rstrip(_TRAILING + " ")
    return path.replace("\\", "/").strip("/")


def find_local_paths(text: str, prose: bool = True) -> list[Ref]:
    """C:\\FMEData paths in text. prose=False (workspaces) skips the sentence-end rules, which would cut 'St. Louis.shp'."""
    refs = []
    for n, line in _lines(text):
        for m in _LOCAL_RE.finditer(line):
            rel = _clean_local(m.group(1), prose)
            if rel:
                refs.append(Ref(n, m.group(0), rel))
    return refs


def _strip_url_end(url: str) -> str:
    """Drop sentence punctuation after a URL, but keep a ')' that closes a '(' inside it (Battleship_(game))."""
    while url and url[-1] in _TRAILING:
        if url[-1] == ")" and url.count("(") >= url.count(")"):
            break
        url = url[:-1]
    return url


def _urls(text: str):
    for n, line in _lines(text):
        for m in _URL_RE.finditer(line):
            for part in m.group(0).split(","):
                part = _strip_url_end(part)
                if part.startswith("http"):
                    yield n, part


def find_s3_urls(text: str) -> list[Ref]:
    refs = []
    for n, url in _urls(text):
        if S3_FMEDATA not in url:
            continue
        path = urllib.parse.unquote(url.split("?", 1)[0].split("#", 1)[0])
        rel = path.split(S3_MAIN_PREFIX, 1)[1] if S3_MAIN_PREFIX in path else ""
        refs.append(Ref(n, url, rel.strip("/")))
    return refs


def find_web_urls(text: str) -> list[Ref]:
    return [Ref(n, url, "") for n, url in _urls(text) if S3_FMEDATA not in url]
