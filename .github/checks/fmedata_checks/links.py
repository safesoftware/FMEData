"""Check web links: fetch each unique URL once and classify the answer."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, Literal

from .model import Config

LinkStatus = Literal["ok", "broken", "bot-refused", "local", "error"]
Fetch = Callable[[str], "int | None"]

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
_USER_AGENT = "FMEData-link-check/1.0"


def classify_url(url: str, status: int | None, cfg: Config) -> LinkStatus:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host in _LOCAL_HOSTS:
        return "local"
    if status is None:
        return "error"
    if status in (401, 403) and any(host == h or host.endswith("." + h) for h in cfg.bot_refusers):
        return "bot-refused"
    return "broken" if status >= 400 else "ok"


def http_status(url: str, timeout: float = 10.0) -> int | None:
    """HEAD the URL (GET when HEAD isn't allowed); the final status, or None when nothing answers."""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return e.code
        except (urllib.error.URLError, OSError, ValueError):
            return None
    return None


def check_urls(urls: Iterable[str], fetch: Fetch = http_status, workers: int = 8) -> dict[str, int | None]:
    unique = sorted(set(urls))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return dict(zip(unique, pool.map(fetch, unique)))
