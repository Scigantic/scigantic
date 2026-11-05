"""Command line entry point: scigantic open | search | info | files.

Exit codes: 0 success, 1 the catalog refused or could not be reached
(the reason is printed), 2 the reference could not be parsed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from typing import List, Optional

from . import catalog
from ._version import __version__
from .catalog import SciganticError
from .refs import InvalidReference, parse


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scigantic", description="Open public datasets in a browser notebook.")
    p.add_argument("--version", action="version", version=f"scigantic {__version__}")
    p.add_argument("--api-url", help="catalog API base (default https://api.scigantic.com, or SCIGANTIC_API_URL)")
    p.add_argument(
        "--site-url", help="site base for landing URLs (default https://scigantic.com, or SCIGANTIC_SITE_URL)"
    )
    p.add_argument("--timeout", type=float, default=catalog.TIMEOUT, help="seconds per API request")
    sub = p.add_subparsers(dest="command", required=True)

    o = sub.add_parser("open", help="print the Scigantic page for a dataset and open it in the browser")
    o.add_argument("ref", help="hf:owner/repo, owner/repo, a huggingface.co dataset URL, or an archive id")
    o.add_argument("--no-browser", action="store_true", help="print the URL only")
    o.add_argument("--json", action="store_true", help="resolve through the API and print its JSON reply")

    s = sub.add_parser("search", help="search the Scigantic catalog")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--json", action="store_true", help="print the rows as JSON")

    i = sub.add_parser("info", help="show the catalog record for a dataset")
    i.add_argument("ref")

    f = sub.add_parser("files", help="list the files of a Hugging Face dataset (needs scigantic[hf])")
    f.add_argument("ref")
    f.add_argument("--revision", help="branch, tag or commit (default: main)")
    return p


def _cmd_open(args: argparse.Namespace) -> int:
    ref = parse(args.ref)
    if args.json:
        from . import resolve

        payload = resolve(args.ref, timeout=args.timeout)
        print(json.dumps(payload, indent=2, sort_keys=True))
        url = str(payload.get("archiveUrl") or ref.landing_url)
    else:
        url = ref.landing_url
        print(url)
    if not args.no_browser:
        webbrowser.open(url)
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    rows = catalog.search(args.query, limit=args.limit, timeout=args.timeout)
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0 if rows else 1
    if not rows:
        print("no results", file=sys.stderr)
        return 1
    for r in rows:
        print(f"{r.get('id', '')}  {r.get('title', '')}")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    ref = parse(args.ref)
    if ref.kind == "hf":
        payload = catalog.resolve_hf(ref.owner, ref.repo, timeout=args.timeout)
        item = catalog.get(str(payload.get("archiveId", "")), timeout=args.timeout)
    else:
        item = catalog.get(ref.archive_id, timeout=args.timeout)
    keep = ("id", "title", "category", "author", "license", "cloudProvider", "bucketName", "huggingFaceUrl", "unlisted")
    print(json.dumps({k: item.get(k) for k in keep if k in item}, indent=2, sort_keys=True))
    return 0


def _cmd_files(args: argparse.Namespace) -> int:
    from . import hf

    for path in hf.files(args.ref, revision=args.revision):
        print(path)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.api_url:
        os.environ["SCIGANTIC_API_URL"] = args.api_url
    if args.site_url:
        os.environ["SCIGANTIC_SITE_URL"] = args.site_url
    try:
        if args.command == "open":
            return _cmd_open(args)
        if args.command == "search":
            return _cmd_search(args)
        if args.command == "info":
            return _cmd_info(args)
        if args.command == "files":
            return _cmd_files(args)
    except InvalidReference as e:
        print(f"scigantic: {e}", file=sys.stderr)
        return 2
    except ImportError as e:
        print(f"scigantic: {e}", file=sys.stderr)
        return 1
    except SciganticError as e:
        print(f"scigantic: {e.reason}: {e}", file=sys.stderr)
        if e.huggingface_url:
            print(f"source: {e.huggingface_url}", file=sys.stderr)
        if e.retry_after:
            print(f"retry after: {int(e.retry_after)} s", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
