# Stage-2 Pipeline — Implementation Plan (Archive)

This archive describes how to implement **Stage‑2: normalization + deduplication** for the design-doc extraction system.

**Ground truth reference:** `model_and_storage_spec.md` (provided in the project). This plan intentionally stays *implementation-flexible*: it defines **contracts, responsibilities, and decision rules**, while allowing your coding agent to reuse existing DB/Qdrant wrappers and table names.

## What Stage‑2 must do (in one sentence)
Stage‑2 takes Stage‑1 *claim cards* (explicit, chunk-local) and produces **canonical IDs** via `review_status` + `superseded_by` chains, plus optional **conflict groups**, without rewriting Stage‑1 evidence.

## Pass order (required)
1) Actors
2) Objects
3) States (attached/candidate-mapped to objects)
4) Actions (bound to canonical actor/object IDs)

Stage‑3 (AtomicActions + BusinessOperations composition) is **out of scope**.

## Where the prompts live
Prompts are explicit and stored in `./prompts/`:

- `prompts/actor_resolution.md`
- `prompts/object_resolution.md`
- `prompts/state_resolution.md`
- `prompts/action_resolution.md`
- `prompts/output_schema.md` (shared JSON output contract)
- `prompts/common_instructions.md` (shared constraints + anti-hallucination rules)

The orchestration docs reference these files rather than embedding prompts inline.

## Files index
- `01_scope_and_principles.md`
- `02_stage2_data_model_expectations.md`
- `03_pipeline_control_flow.md`
- `04_context_pack_builder.md`
- `05_pass_actor.md`
- `06_pass_object.md`
- `07_pass_state.md`
- `08_pass_action.md`
- `09_storage_updates_and_idempotency.md`
- `10_metrics_and_quality_gates.md`
- `prompts/*`
