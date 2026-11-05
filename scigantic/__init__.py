"""scigantic: open a public dataset in a browser notebook with the files already mounted."""

from __future__ import annotations

import webbrowser
from typing import Any, Dict

from . import catalog as _catalog
from ._version import __version__
from .catalog import SciganticError
from .refs import DatasetRef, InvalidReference, parse

__all__ = ["__version__", "open", "url_for", "resolve", "parse", "DatasetRef", "InvalidReference", "SciganticError"]


def url_for(ref: str) -> str:
    """The Scigantic landing page for a dataset. Pure string work, no network."""
    return parse(ref).landing_url


def resolve(ref: str, timeout: float = _catalog.TIMEOUT) -> Dict[str, Any]:
    """Ask the catalog for the archive behind a dataset, creating it on first request.

    Returns the API payload. Raises SciganticError with `reason` set to the API's
    code (private, gated, disabled, not_found, license, too_large, invalid_repo,
    rate_limited, upstream_error) when the dataset cannot be served.
    """
    r = parse(ref)
    if r.kind == "hf":
        return _catalog.resolve_hf(r.owner, r.repo, timeout=timeout)
    item = _catalog.get(r.archive_id, timeout=timeout)
    return {
        "success": True,
        "archiveId": item.get("id", r.archive_id),
        "created": False,
        "archiveUrl": r.landing_url,
        "title": item.get("title", ""),
        "license": item.get("license"),
        "unlisted": bool(item.get("unlisted", False)),
    }


def _in_notebook() -> bool:
    try:
        from IPython import get_ipython
    except ImportError:
        return False
    shell = get_ipython()
    return bool(shell) and type(shell).__name__ == "ZMQInteractiveShell"


def open(ref: str, browser: bool = True) -> str:
    """Open the dataset's Scigantic page and return its URL.

    In a terminal this opens the default browser. Inside a Jupyter kernel there
    is no browser to open, so the URL is shown as a clickable link instead.
    """
    url = url_for(ref)
    if browser:
        if _in_notebook():
            from IPython.display import HTML, display

            display(HTML(f'<a href="{url}" target="_blank" rel="noopener">{url}</a>'))
        else:
            webbrowser.open(url)
    return url
