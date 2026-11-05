"""Read-only access to the public Scigantic catalog API."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .refs import API_URL

__version__ = "0.1.0"
USER_AGENT = f"scigantic-py/{__version__}"
TIMEOUT = 10.0


class SciganticError(Exception):
    """A request the catalog refused. `reason` is the API's machine-readable code."""

    def __init__(self, message: str, reason: str = "error", status: int = 0, payload: Optional[dict] = None):
        super().__init__(message)
        self.reason = reason
        self.status = status
        self.payload = payload or {}


def _request(url: str) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {}
        reason = str(payload.get("reason") or ("not_found" if e.code == 404 else "error"))
        message = str(payload.get("message") or payload.get("error") or f"HTTP {e.code} from {url}")
        raise SciganticError(message, reason=reason, status=e.code, payload=payload) from None
    except urllib.error.URLError as e:
        raise SciganticError(f"could not reach {url}: {e.reason}", reason="network") from None


def _unwrap(payload: Dict[str, Any]) -> Any:
    # /api/archives/<id> answers either {"data": {...}} or the item itself.
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    q = urllib.parse.urlencode({"search": query, "limit": int(limit)})
    data = _unwrap(_request(f"{API_URL}/api/archives?{q}"))
    return list(data) if isinstance(data, list) else []


def get(archive_id: str) -> Dict[str, Any]:
    data = _unwrap(_request(f"{API_URL}/api/archives/{urllib.parse.quote(archive_id)}"))
    if not isinstance(data, dict):
        raise SciganticError(f"unexpected response for archive {archive_id}", reason="error")
    return data


def resolve_hf(owner: str, repo: str) -> Dict[str, Any]:
    return _request(f"{API_URL}/api/hf/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}")
