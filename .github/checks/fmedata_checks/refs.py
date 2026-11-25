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
_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
_EXT_THEN_SPACE = re.compile(r"^(.*?\.[A-Za-z0-9]{1,8})(?=\s)")
_TRAILING = ".,;:)]"


USER_PATH_RE = re.compile(r"([Cc]:[\\/]Users[\\/])([^\\/\"'<>\r\n]+?)(?=[\\/])")


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


def _clean_local(captured: str) -> str:
    path = captured.strip()
    # Prose after a path ("...\Parks.shp in Workbench"): stop after the first file name with an extension.
    m = _EXT_THEN_SPACE.match(path)
    if m and "\\" not in path[m.end():] and "/" not in path[m.end():]:
        path = m.group(1)
    path = path.rstrip(_TRAILING + " ")
    return path.replace("\\", "/").strip("/")


def find_local_paths(text: str) -> list[Ref]:
    refs = []
    for n, line in _lines(text):
        for m in _LOCAL_RE.finditer(line):
            rel = _clean_local(m.group(1))
            if rel:
                refs.append(Ref(n, m.group(0), rel))
    return refs


def _urls(text: str):
    for n, line in _lines(text):
        for m in _URL_RE.finditer(line):
            for part in m.group(0).split(","):
                part = part.rstrip(_TRAILING)
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
