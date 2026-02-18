"""CLI for Stage 1 extraction: stage1_extract --doc-id <id> [options]."""
from __future__ import annotations

import argparse
import json
import sys
from uuid import uuid4

from app.db.session import init_db
from app.stage1 import run_stage1_extract
from app.stage1.config import Stage1Config


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1: Chunk → Claim Ledger extraction")
    parser.add_argument("--doc-id", required=True, help="Document ID to process")
    parser.add_argument("--model", dest="model_id", default="ollama/llama3.2", help="Model id (e.g. ollama/llama3.2)")
    parser.add_argument("--prompt-version", default="chunk_claims_extract_v1", help="Prompt version")
    parser.add_argument("--chunk-ids", nargs="*", help="Optional list of chunk IDs (default: all chunks)")
    parser.add_argument("--pending", action="store_true", help="Process only chunks without successful cache for current signature")
    parser.add_argument("--force", action="store_true", help="Bypass cache (add nonce to signature)")
    parser.add_argument("--no-embed", action="store_true", dest="no_embed", help="Skip embedding claims into Qdrant")
    parser.add_argument("--temperature", type=float, default=0.1, help="LLM temperature")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max output tokens")
    parser.add_argument("--debug", action="store_true", help="Turn on LiteLLM debug logging (verbose request/response)")
    args = parser.parse_args()

    if args.debug:
        import litellm
        litellm._turn_on_debug()
        print("LiteLLM debug mode ON (verbose logging)", file=sys.stderr)

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


if __name__ == "__main__":
    sys.exit(main())
