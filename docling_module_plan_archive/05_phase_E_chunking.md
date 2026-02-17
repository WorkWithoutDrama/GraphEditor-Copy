# 05 — Phase E: Chunking (artifacts → chunks + embedding-ready text)

## E0. Outcomes
- Chunk using Docling’s structure-aware chunkers by default.
- Produce embedding-ready text; store in **Chunk.text** (or Chunk.text_uri for very large chunks). Plan’s “text_for_embedding” = value used for embedding and for **chunk_hash**.
- Enforce hard max tokens to protect embedding calls (tokenizer from embeddings/embedding_set).

Docling chunking guide and HybridChunker notes: citeturn0search4turn0search1

---

## E1. Chunker strategy (default)

Default to **HybridChunker**:
- structure-first hierarchical chunking
- tokenization-aware refinements
- supports contextualization/serialization

Fallback to **HierarchicalChunker** if tokenizer deps not available.

Implementation detail:
- keep chunker selection in `ChunkerFactory(settings)`.

Acceptance:
- Same input + same settings → same chunk sequence.

---

## E2. Tokenizer alignment (embeddings module owns tokenizer)

**Tokenizer is owned by the embeddings module.** Docling receives a **TokenizerSpec** (resolved from `embedding_set_id` via shared config or a port) and uses it only for:
- computing token count for chunk sizing
- enforcing hard max tokens

Do not duplicate embedding model selection in Docling. Same tokenizer as embedding provider → very low “input too long” failures.

Acceptance:
- Very low rate of “input too long” embedding failures.

---

## E3. Hard max token enforcement (must-have)

Docling core has historically discussed cases where `max_tokens` may not be strictly enforced. (Example: docling-core issue notes.)  
Therefore:

Algorithm:
1) Let Docling chunker produce candidate chunks.
2) Compute token count for `text_for_embedding`.
3) If `token_count > max_tokens`:
   - apply a deterministic fallback splitter:
     - split by paragraphs/sentences
     - then by token-window with overlap
4) Recompute chunk_index and chunk_hash (see E6).

Acceptance:
- No chunk exceeds `max_tokens` hard limit.

---

## E4. Contextualized text_for_embedding

Use Docling contextualization when available:
- add breadcrumbs (section headings), captions, page numbers, table titles, etc.

Store the **embedding-ready** (contextualized) string in **Chunk.text** by default — breadcrumbs, captions, page numbers, etc. If a chunk is huge, store full text at **text_uri** and keep a short preview in text.

Why:
- retrieval improves (chunk carries “where it came from”)
- generated answers have better grounding

Acceptance:
- A chunk can be interpreted outside original document with context.

---

## E5. Chunk metadata schema (DB: chunk_index, meta_json)

Use **chunk_index** (0..n-1) in DB — plan’s “ordinal” = **chunk_index**. Store in Chunk:
- `chunk_index`, `page_start`, `page_end` (if known)
- **meta_json**: `chunker_version`, `section_path`, `captions`, `source_artifact` (e.g. "structure_json_uri"), optional `token_count`

Acceptance:
- Search UI / debug tooling can show “why we retrieved this”.

---

## E6. Deterministic chunk_hash (collision-safe)

Uniqueness is on `(document_id, chunk_hash)`. To avoid collisions when similar text appears multiple times in one doc:

- **chunk_hash** = `sha256(f"{chunker_version}:{chunk_index}:{text_for_embedding}")`

Same settings + same document → same chunk_index and chunk_hash → idempotent re-runs.

Acceptance:
- Re-chunk with identical settings yields identical chunk_hashes and no duplicate rows.

