"""scigantic: open a public dataset in a browser notebook with the files already mounted."""

from __future__ import annotations

import webbrowser
from typing import Any, Dict

from . import catalog as _catalog
from .catalog import SciganticError
from .refs import DatasetRef, InvalidReference, parse

__version__ = "0.1.0"
__all__ = ["open", "url_for", "resolve", "parse", "DatasetRef", "InvalidReference", "SciganticError"]


def url_for(ref: str) -> str:
    """The Scigantic landing page for a dataset. Pure string work, no network."""
    return parse(ref).landing_url


def resolve(ref: str) -> Dict[str, Any]:
    """Ask the catalog for the archive behind a dataset, creating it on first request.

    Returns the API payload. Raises SciganticError with `reason` set to the API's
    code (private, gated, disabled, not_found, license, too_large, invalid_repo,
    rate_limited) when the dataset cannot be served.
    """
    r = parse(ref)
    if r.kind == "hf":
        return _catalog.resolve_hf(r.owner, r.repo)
    item = _catalog.get(r.archive_id)
    return {
        "success": True,
        "archiveId": item.get("id", r.archive_id),
        "created": False,
        "archiveUrl": r.landing_url,
        "title": item.get("title", ""),
    }


def open(ref: str, browser: bool = True) -> str:
    """Open the dataset's Scigantic page in the default browser and return its URL."""
    url = url_for(ref)
    if browser:
        webbrowser.open(url)
    return url
