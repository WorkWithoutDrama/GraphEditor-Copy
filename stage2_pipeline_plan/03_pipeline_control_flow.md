# 03 — Pipeline Control Flow

Stage‑2 runs as a deterministic batch pipeline with four ordered passes:
1) ACTOR resolution
2) OBJECT resolution
3) STATE resolution
4) ACTION resolution

Each pass:
- selects seed claims (primarily `review_status=UNREVIEWED`)
- retrieves similar candidates from Qdrant
- fetches full evidence from SQL
- calls the LLM with a strict prompt & output schema
- applies changes in SQL transaction(s) + writes decision audit

## Recommended structure
- `Stage2Runner`
  - `run_pass_actor()`
  - `run_pass_object()`
  - `run_pass_state()`
  - `run_pass_action()`

Shared helpers:
- `ClaimRepo` (SQL reads/writes)
- `QdrantRepo` (vector search + payload filters)
- `ContextPackBuilder`
- `LLMClient`
- `DecisionApplier`

## Seed selection strategies (choose one)
- Simple iteration by created_at / chunk_index
- High-leverage first (by dedupe_key frequency / centrality)
- Hybrid

## Concurrency (optional)
Single-threaded is fine for MVP. For concurrency:
- lock or mark seeds IN_PROGRESS
- keep writes idempotent

## Retry policy
- transient LLM failure: retry with backoff
- parse failure: store raw response; mark seed for retry
- ambiguous: DEFER or SPLIT_CONFLICT
