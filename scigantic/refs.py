"""Parse the ways a dataset can be named.

Accepted forms:
    hf:owner/repo
    owner/repo
    https://huggingface.co/datasets/owner/repo[/anything]
    <uuid>                              (a Scigantic archive id)
    https://scigantic.com/archive/<uuid>[/anything]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

SITE_URL = "https://scigantic.com"
API_URL = "https://api.scigantic.com"
HF_URL = "https://huggingface.co"

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_REPO = re.compile(rf"^({_SEGMENT})/({_SEGMENT})$")


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
            return f"{SITE_URL}/hf/{self.owner}/{self.repo}"
        return f"{SITE_URL}/archive/{self.archive_id}"

    @property
    def resolve_url(self) -> str:
        if self.kind == "hf":
            return f"{API_URL}/api/hf/{self.owner}/{self.repo}"
        return f"{API_URL}/api/archives/{self.archive_id}"

    @property
    def huggingface_url(self) -> str:
        return f"{HF_URL}/datasets/{self.owner}/{self.repo}" if self.kind == "hf" else ""


def _hf(owner: str, repo: str) -> DatasetRef:
    return DatasetRef(kind="hf", owner=owner, repo=repo)


def parse(ref: str) -> DatasetRef:
    s = (ref or "").strip()
    if not s:
        raise InvalidReference("empty reference")

    if _UUID.match(s):
        return DatasetRef(kind="archive", archive_id=s.lower())

    if s.lower().startswith("hf:"):
        body = s[3:].lstrip("/")
        m = _REPO.match(body)
        if not m:
            raise InvalidReference(f"not an owner/repo pair: {body!r}")
        return _hf(m.group(1), m.group(2))

    if "://" in s:
        u = urlparse(s)
        host = (u.hostname or "").lower()
        parts = [p for p in u.path.split("/") if p]
        if host in ("huggingface.co", "www.huggingface.co", "hf.co"):
            if len(parts) >= 3 and parts[0] == "datasets":
                return _hf(parts[1], parts[2])
            raise InvalidReference(f"not a dataset URL: {s}")
        if host in ("scigantic.com", "www.scigantic.com") or host.endswith(".scigantic.com"):
            if len(parts) >= 2 and parts[0] == "archive" and _UUID.match(parts[1]):
                return DatasetRef(kind="archive", archive_id=parts[1].lower())
            if len(parts) >= 3 and parts[0] == "hf":
                return _hf(parts[1], parts[2])
            raise InvalidReference(f"not an archive or hf URL: {s}")
        raise InvalidReference(f"unsupported URL: {s}")

    m = _REPO.match(s)
    if m:
        return _hf(m.group(1), m.group(2))

    raise InvalidReference(
        f"could not parse {s!r}; use hf:owner/repo, owner/repo, a huggingface.co dataset URL, "
        "or a Scigantic archive id"
    )
