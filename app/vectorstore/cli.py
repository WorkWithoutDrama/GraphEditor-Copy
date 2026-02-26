"""CLI for reindex and health check."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys


def _run_async(coro):
    return asyncio.run(coro)


def cmd_health(args: argparse.Namespace) -> int:
    """Check Qdrant connectivity."""
    from app.vectorstore import get_vectorstore_repo

    repo = get_vectorstore_repo()
    ok = _run_async(repo.health())
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


def cmd_reindex(args: argparse.Namespace) -> int:
    """Reindex from old collection to new (requires embed + fetch implementations)."""
    print("Reindex CLI: implement embed_fn and fetch_chunk_fn for your app.", file=sys.stderr)
    print("Use app.vectorstore.migrations.reindex_collection() programmatically.", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="vectorstore")
    sub = parser.add_subparsers(dest="command", required=True)

    health_p = sub.add_parser("health", help="Check Qdrant connectivity")
    health_p.set_defaults(func=cmd_health)

    reindex_p = sub.add_parser("reindex", help="Reindex collection (see --help)")
    reindex_p.add_argument("--old", required=True, help="Old collection name")
    reindex_p.add_argument("--new", required=True, help="New collection name")
    reindex_p.add_argument("--workspace-id", required=True, help="Workspace ID filter")
    reindex_p.set_defaults(func=cmd_reindex)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
