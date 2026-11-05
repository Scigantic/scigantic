"""Stream files of a Hugging Face dataset locally over hf:// without downloading the repo.

Built on huggingface_hub's HfFileSystem, so a token in the usual places
(HF_TOKEN, `huggingface-cli login`) is used automatically. Gated or private
repositories raise SciganticError with reason `gated` / `not_found`, the same
codes the hosted path uses.
"""

from __future__ import annotations

import builtins
from typing import Any, Dict, List, Optional

from .catalog import SciganticError
from .refs import parse

_EXTRA_HINT = 'huggingface_hub is not installed. Install the extra: pip install "scigantic[hf]"'


def _fs(token: Optional[str] = None) -> Any:
    try:
        from huggingface_hub import HfFileSystem
    except ImportError as e:  # pragma: no cover - exercised via monkeypatch in tests
        raise ImportError(_EXTRA_HINT) from e
    return HfFileSystem(token=token) if token else HfFileSystem()


def _repo(ref: str) -> str:
    r = parse(ref)
    if r.kind != "hf":
        raise ValueError(f"{ref!r} is a Scigantic archive id, not a Hugging Face dataset")
    return r.hf_repo


def _root(repo: str, revision: Optional[str]) -> str:
    return f"datasets/{repo}@{revision}" if revision else f"datasets/{repo}"


def _translate(err: Exception, repo: str) -> SciganticError:
    name = type(err).__name__
    text = str(err)
    if name in ("GatedRepoError",) or "gated" in text.lower():
        return SciganticError(
            f"{repo} is gated; accept its terms on the Hub and log in with huggingface_hub", reason="gated"
        )
    if name in ("RepositoryNotFoundError", "EntryNotFoundError", "RevisionNotFoundError") or isinstance(
        err, FileNotFoundError
    ):
        return SciganticError(f"{repo}: {text or 'not found'}", reason="not_found")
    return SciganticError(f"{repo}: {text}", reason="error")


def files(ref: str, detail: bool = False, revision: Optional[str] = None, token: Optional[str] = None) -> List[Any]:
    """List every file in the dataset repository (recursive), as repo-relative paths."""
    repo = _repo(ref)
    fs = _fs(token)
    root = _root(repo, revision)
    try:
        entries = fs.find(root, detail=detail)
    except Exception as e:
        raise _translate(e, repo) from e
    if detail:
        return list(entries.values()) if isinstance(entries, dict) else list(entries)
    prefix = root + "/"
    return [p[len(prefix) :] if p.startswith(prefix) else p for p in entries]


def info(ref: str, path: str, revision: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
    """Size and metadata of one file without reading it."""
    repo = _repo(ref)
    fs = _fs(token)
    try:
        return dict(fs.info(f"{_root(repo, revision)}/{path.lstrip('/')}"))
    except Exception as e:
        raise _translate(e, repo) from e


def open(
    ref: str, path: str, mode: str = "rb", revision: Optional[str] = None, token: Optional[str] = None, **kwargs: Any
) -> Any:
    """Open one file in the dataset as a file-like object backed by HTTP range reads."""
    repo = _repo(ref)
    if mode not in ("r", "rb", "rt"):
        raise ValueError("datasets are read-only here; use mode 'rb' or 'r'")
    fs = _fs(token)
    try:
        return fs.open(f"{_root(repo, revision)}/{path.lstrip('/')}", mode=mode, **kwargs)
    except Exception as e:
        raise _translate(e, repo) from e


# Keep the builtin reachable for callers who imported this module's `open`.
builtin_open = builtins.open
