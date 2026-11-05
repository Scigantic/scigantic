"""Read-only access to the public Scigantic catalog API.

Every call goes through `request`, which retries transient failures (network
errors and 5xx answers) with a short backoff, and turns the API's refusal
bodies into SciganticError with a machine-readable `reason`.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ._version import __version__
from .refs import api_url

USER_AGENT = f"scigantic-py/{__version__}"
TIMEOUT = 10.0
RETRIES = 3
BACKOFF_SECONDS = 0.5
RETRY_STATUSES = frozenset({502, 503, 504})

log = logging.getLogger("scigantic")


class SciganticError(Exception):
    """A request the catalog refused or could not complete.

    `reason` is the API's machine-readable code (private, gated, disabled,
    not_found, license, too_large, invalid_repo, rate_limited, upstream_error),
    or `network` / `error` when no answer arrived. `retry_after` is set, in
    seconds, when the API said when to try again.
    """

    def __init__(
        self,
        message: str,
        reason: str = "error",
        status: int = 0,
        payload: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None,
    ):
        super().__init__(message)
        self.reason = reason
        self.status = status
        self.payload = payload or {}
        self.retry_after = retry_after

    @property
    def huggingface_url(self) -> str:
        return str(self.payload.get("huggingFaceUrl") or "")


def _retry_after(headers: Any) -> Optional[float]:
    try:
        raw = headers.get("Retry-After") if headers is not None else None
        return float(raw) if raw else None
    except (TypeError, ValueError):
        return None


def request(url: str, timeout: float = TIMEOUT, retries: int = RETRIES) -> Dict[str, Any]:
    """GET a JSON document. Retries network errors and 5xx up to `retries` times."""
    attempt = 0
    while True:
        attempt += 1
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                try:
                    data = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    raise SciganticError(
                        f"{url} did not return JSON", reason="error", status=getattr(resp, "status", 0)
                    ) from None
                return data if isinstance(data, dict) else {"data": data}
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode("utf-8"))
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}
            if e.code in RETRY_STATUSES and attempt <= retries:
                log.debug("retrying %s after HTTP %s (attempt %d)", url, e.code, attempt)
                time.sleep(BACKOFF_SECONDS * attempt)
                continue
            reason = str(
                payload.get("reason")
                or ("not_found" if e.code == 404 else "rate_limited" if e.code == 429 else "error")
            )
            err_obj = payload.get("error")
            err: Dict[str, Any] = err_obj if isinstance(err_obj, dict) else {}
            message = str(
                payload.get("message") or err.get("message") or payload.get("error") or f"HTTP {e.code} from {url}"
            )
            raise SciganticError(
                message, reason=reason, status=e.code, payload=payload, retry_after=_retry_after(e.headers)
            ) from None
        except urllib.error.URLError as e:
            if attempt <= retries:
                log.debug("retrying %s after %s (attempt %d)", url, e.reason, attempt)
                time.sleep(BACKOFF_SECONDS * attempt)
                continue
            raise SciganticError(f"could not reach {url}: {e.reason}", reason="network") from None
        except TimeoutError:
            if attempt <= retries:
                time.sleep(BACKOFF_SECONDS * attempt)
                continue
            raise SciganticError(f"timed out reaching {url}", reason="network") from None


# 0.1.x name, kept for callers.
_request = request


def _unwrap(payload: Dict[str, Any]) -> Any:
    # /api/archives/<id> answers either {"data": {...}} or the item itself.
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def search(query: str, limit: int = 10, timeout: float = TIMEOUT) -> List[Dict[str, Any]]:
    """Search the public catalog. Returns archive rows (possibly empty)."""
    if not (query or "").strip():
        return []
    q = urllib.parse.urlencode({"search": query.strip(), "limit": max(1, min(int(limit), 100))})
    data = _unwrap(request(f"{api_url()}/api/archives?{q}", timeout=timeout))
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def get(archive_id: str, timeout: float = TIMEOUT) -> Dict[str, Any]:
    """One archive row by id. Raises SciganticError(reason='not_found') if absent."""
    data = _unwrap(request(f"{api_url()}/api/archives/{urllib.parse.quote(archive_id, safe='')}", timeout=timeout))
    if not isinstance(data, dict) or not data:
        raise SciganticError(f"unexpected response for archive {archive_id}", reason="error")
    return data


def resolve_hf(owner: str, repo: str, timeout: float = TIMEOUT) -> Dict[str, Any]:
    """Resolve owner/repo to an archive, creating it on first request."""
    url = f"{api_url()}/api/hf/{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(repo, safe='')}"
    return request(url, timeout=timeout)
