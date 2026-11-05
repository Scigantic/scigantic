"""Command line entry point: scigantic open | search | info."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from typing import List, Optional

from . import __version__, catalog
from .catalog import SciganticError
from .refs import InvalidReference, parse


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scigantic", description="Open public datasets in a browser notebook.")
    p.add_argument("--version", action="version", version=f"scigantic {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    o = sub.add_parser("open", help="print the Scigantic page for a dataset and open it in the browser")
    o.add_argument("ref", help="hf:owner/repo, owner/repo, a huggingface.co dataset URL, or an archive id")
    o.add_argument("--no-browser", action="store_true", help="print the URL only")
    o.add_argument("--json", action="store_true", help="resolve through the API and print its JSON reply")

    s = sub.add_parser("search", help="search the Scigantic catalog")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)

    i = sub.add_parser("info", help="show the catalog record for a dataset")
    i.add_argument("ref")
    return p


def _cmd_open(args: argparse.Namespace) -> int:
    ref = parse(args.ref)
    if args.json:
        from . import resolve

        payload = resolve(args.ref)
        print(json.dumps(payload, indent=2, sort_keys=True))
        url = payload.get("archiveUrl") or ref.landing_url
    else:
        url = ref.landing_url
        print(url)
    if not args.no_browser:
        webbrowser.open(url)
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    rows = catalog.search(args.query, limit=args.limit)
    if not rows:
        print("no results", file=sys.stderr)
        return 1
    for r in rows:
        print(f"{r.get('id', '')}  {r.get('title', '')}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    ref = parse(args.ref)
    if ref.kind == "hf":
        payload = catalog.resolve_hf(ref.owner, ref.repo)
        item = catalog.get(str(payload.get("archiveId", "")))
    else:
        item = catalog.get(ref.archive_id)
    keep = ("id", "title", "category", "author", "license", "cloudProvider", "bucketName", "huggingFaceUrl")
    print(json.dumps({k: item.get(k) for k in keep if k in item}, indent=2, sort_keys=True))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "open":
            return _cmd_open(args)
        if args.command == "search":
            return _cmd_search(args)
        if args.command == "info":
            return _cmd_info(args)
    except InvalidReference as e:
        print(f"scigantic: {e}", file=sys.stderr)
        return 2
    except SciganticError as e:
        print(f"scigantic: {e.reason}: {e}", file=sys.stderr)
        if e.payload.get("huggingFaceUrl"):
            print(f"source: {e.payload['huggingFaceUrl']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
