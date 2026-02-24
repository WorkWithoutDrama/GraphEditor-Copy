"""CLI for Stage 1 extraction and claim indexing: stage1_extract, stage1_index_qdrant."""
from __future__ import annotations

import argparse
import json
import sys
from uuid import uuid4

from app.db.session import init_db
from app.stage1 import run_stage1_extract
from app.stage1.config import Stage1Config


def cmd_extract(args: argparse.Namespace) -> int:
    init_db()
    config = Stage1Config(
        model_id=args.model_id,
        prompt_version=args.prompt_version,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        embed_claims=not args.no_embed,
        force_nonce=str(uuid4()) if args.force else None,
    )
    try:
        result = run_stage1_extract(
            args.doc_id,
            config,
            chunk_ids=args.chunk_ids or None,
            pending_only=args.pending,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"run_id={result.run_id}")
    print(f"status={result.status}")
    if result.stats:
        print(json.dumps(result.stats, indent=2))
    if result.error_summary:
        print(f"error_summary={result.error_summary}", file=sys.stderr)
    return 0 if result.status in ("SUCCESS", "PARTIAL") else 1


def cmd_index_qdrant(args: argparse.Namespace) -> int:
    init_db()
    from app.stage1.claim_index import index_stage1_claims_to_qdrant

    stats = index_stage1_claims_to_qdrant(
        args.run_id,
        only_pending=not args.all,
        collection_name=args.collection or None,
    )
    print(f"claims_total={stats.claims_total}")
    print(f"claims_indexed={stats.claims_indexed}")
    print(f"claims_failed={stats.claims_failed}")
    if stats.error_summary:
        print(f"error_summary={stats.error_summary}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1: Chunk → Claim Ledger extraction and Qdrant indexing")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # stage1 extract (default for backward compat)
    extract_parser = subparsers.add_parser("extract", help="Run Stage 1 extraction for a document")
    extract_parser.add_argument("--doc-id", required=True, help="Document ID to process")
    extract_parser.add_argument("--model", dest="model_id", default="ollama/llama3.2", help="Model id")
    extract_parser.add_argument("--prompt-version", default="chunk_claims_extract_v1", help="Prompt version")
    extract_parser.add_argument("--chunk-ids", nargs="*", help="Optional list of chunk IDs")
    extract_parser.add_argument("--pending", action="store_true", help="Process only chunks without successful cache")
    extract_parser.add_argument("--force", action="store_true", help="Bypass cache (add nonce to signature)")
    extract_parser.add_argument("--no-embed", action="store_true", dest="no_embed", help="Skip embedding claims into Qdrant")
    extract_parser.add_argument("--temperature", type=float, default=0.1, help="LLM temperature")
    extract_parser.add_argument("--max-tokens", type=int, default=4096, help="Max output tokens")
    extract_parser.add_argument("--debug", action="store_true", help="Turn on LiteLLM debug logging")
    extract_parser.set_defaults(func=cmd_extract)

    # stage1 index_qdrant
    index_parser = subparsers.add_parser("index_qdrant", help="Index run claims to Qdrant (stage1_cards)")
    index_parser.add_argument("--run-id", required=True, help="Pipeline run ID")
    index_parser.add_argument("--all", action="store_true", help="Index all claims (default: only pending)")
    index_parser.add_argument("--collection", default=None, help="Qdrant collection name (default: stage1_cards)")
    index_parser.set_defaults(func=cmd_index_qdrant)

    argv = sys.argv[1:]
    if argv and argv[0] in ("extract", "index_qdrant"):
        args = parser.parse_args()
    else:
        # Backward compat: no subcommand -> extract (e.g. --doc-id xxx)
        args = parser.parse_args(["extract"] + argv)

    if args.command == "extract" and getattr(args, "debug", False):
        import litellm
        litellm._turn_on_debug()
        print("LiteLLM debug mode ON (verbose logging)", file=sys.stderr)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
