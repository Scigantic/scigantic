"""Parse the ways a dataset can be named.

Accepted forms:
    hf:owner/repo
    hf://owner/repo
    hf://datasets/owner/repo
    owner/repo
    https://huggingface.co/datasets/owner/repo[/anything][?query]
    <uuid>                              (a Scigantic archive id)
    https://scigantic.com/archive/<uuid>[/anything]
    https://scigantic.com/hf/owner/repo

The site and API hosts can be overridden with SCIGANTIC_SITE_URL and
SCIGANTIC_API_URL (for example to point at a staging deployment).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_SITE_URL = "https://scigantic.com"
DEFAULT_API_URL = "https://api.scigantic.com"
HF_URL = "https://huggingface.co"

# Kept for callers that imported the constants from 0.1.x.
SITE_URL = DEFAULT_SITE_URL
API_URL = DEFAULT_API_URL

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
# Hub repo ids: each segment is 1-96 chars of [A-Za-z0-9._-], never starting
# with a dot or a dash and never containing "..". Same rule as the server.
_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}"
_REPO = re.compile(rf"^({_SEGMENT})/({_SEGMENT})$")


def site_url() -> str:
    return (os.environ.get("SCIGANTIC_SITE_URL") or DEFAULT_SITE_URL).rstrip("/")


def api_url() -> str:
    return (os.environ.get("SCIGANTIC_API_URL") or DEFAULT_API_URL).rstrip("/")


class InvalidReference(ValueError):
    """The string names neither a Hugging Face dataset nor a Scigantic archive."""


@dataclass(frozen=True)
class DatasetRef:
    kind: str  # "hf" or "archive"
    owner: str = ""
    repo: str = ""
    archive_id: str = ""

    @property
    def hf_repo(self) -> str:
        return f"{self.owner}/{self.repo}" if self.kind == "hf" else ""

    @property
    def landing_url(self) -> str:
        if self.kind == "hf":
            return f"{site_url()}/hf/{self.owner}/{self.repo}"
        return f"{site_url()}/archive/{self.archive_id}"

    @property
    def resolve_url(self) -> str:
        if self.kind == "hf":
            return f"{api_url()}/api/hf/{self.owner}/{self.repo}"
        return f"{api_url()}/api/archives/{self.archive_id}"

    @property
    def huggingface_url(self) -> str:
        return f"{HF_URL}/datasets/{self.owner}/{self.repo}" if self.kind == "hf" else ""

    def __str__(self) -> str:
        return self.hf_repo if self.kind == "hf" else self.archive_id


def _hf(owner: str, repo: str) -> DatasetRef:
    if ".." in owner or ".." in repo:
        raise InvalidReference(f"not an owner/repo pair: {owner}/{repo}")
    return DatasetRef(kind="hf", owner=owner, repo=repo)


def _repo_pair(body: str) -> DatasetRef:
    m = _REPO.match(body)
    if not m:
        raise InvalidReference(f"not an owner/repo pair: {body!r}")
    return _hf(m.group(1), m.group(2))


def parse(ref: str) -> DatasetRef:
    s = (ref or "").strip()
    if not s:
        raise InvalidReference("empty reference")

    if _UUID.match(s):
        return DatasetRef(kind="archive", archive_id=s.lower())

    if s.lower().startswith("hf:"):
        body = s[3:].lstrip("/")
        if body.startswith("datasets/"):
            body = body[len("datasets/") :]
        return _repo_pair(body.split("?", 1)[0].rstrip("/"))

    if "://" in s:
        u = urlparse(s)
        host = (u.hostname or "").lower()
        parts = [p for p in u.path.split("/") if p]
        if host in ("huggingface.co", "www.huggingface.co", "hf.co"):
            if len(parts) >= 3 and parts[0] == "datasets":
                return _repo_pair(f"{parts[1]}/{parts[2]}")
            raise InvalidReference(f"not a dataset URL: {s}")
        site = urlparse(site_url()).hostname or "scigantic.com"
        if host in (site, f"www.{site}") or host.endswith(f".{site}"):
            if len(parts) >= 2 and parts[0] == "archive" and _UUID.match(parts[1]):
                return DatasetRef(kind="archive", archive_id=parts[1].lower())
            if len(parts) >= 3 and parts[0] == "hf":
                return _repo_pair(f"{parts[1]}/{parts[2]}")
            raise InvalidReference(f"not an archive or hf URL: {s}")
        raise InvalidReference(f"unsupported URL: {s}")

    m = _REPO.match(s)
    if m:
        return _hf(m.group(1), m.group(2))

    raise InvalidReference(
        f"could not parse {s!r}; use hf:owner/repo, owner/repo, a huggingface.co dataset URL, or a Scigantic archive id"
    )
