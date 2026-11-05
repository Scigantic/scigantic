"""Stream files of a Hugging Face dataset locally over hf:// without downloading the repo."""

from __future__ import annotations

import builtins
from typing import Any, List

from .refs import parse

_EXTRA_HINT = (
    "huggingface_hub is not installed. Install the extra: pip install \"scigantic[hf]\""
)


def _fs() -> Any:
    try:
        from huggingface_hub import HfFileSystem
    except ImportError as e:  # pragma: no cover - exercised via monkeypatch in tests
        raise ImportError(_EXTRA_HINT) from e
    return HfFileSystem()


def _repo(ref: str) -> str:
    r = parse(ref)
    if r.kind != "hf":
        raise ValueError(f"{ref!r} is a Scigantic archive id, not a Hugging Face dataset")
    return r.hf_repo


def files(ref: str, detail: bool = False) -> List[Any]:
    """List every file in the dataset repository (recursive)."""
    repo = _repo(ref)
    fs = _fs()
    root = f"datasets/{repo}"
    entries = fs.find(root, detail=detail)
    if detail:
        return list(entries.values()) if isinstance(entries, dict) else list(entries)
    prefix = root + "/"
    return [p[len(prefix):] if p.startswith(prefix) else p for p in entries]


def open(ref: str, path: str, mode: str = "rb", **kwargs: Any):
    """Open one file in the dataset as a file-like object backed by HTTP range reads."""
    repo = _repo(ref)
    if mode not in ("r", "rb", "rt"):
        raise ValueError("datasets are read-only here; use mode 'rb' or 'r'")
    fs = _fs()
    return fs.open(f"datasets/{repo}/{path.lstrip('/')}", mode=mode, **kwargs)


# Keep the builtin reachable for callers who imported this module's `open`.
builtin_open = builtins.open
