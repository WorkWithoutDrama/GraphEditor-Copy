"""
Temporary script: extract llm_calls after 2026-02-25 23:50:21, compare valid vs empty prompts,
and analyse prompt text for possible build errors.

Use .venv and run from project root:
  .venv\\Scripts\\python.exe temp_analyze_llm_prompts.py
  (or: .venv\\Scripts\\activate  then  python temp_analyze_llm_prompts.py)

Output: temp_llm_prompt_analysis.txt, temp_prompt_dumps.txt
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Run from project root so app is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db.session import session_scope, init_db
from app.db.models.claim import LlmCall
from sqlalchemy import select

CUTOFF = datetime(2026, 2, 25, 23, 50, 21, 526707)
OUTPUT_FILE = Path(__file__).resolve().parent / "temp_llm_prompt_analysis.txt"
DUMPS_FILE = Path(__file__).resolve().parent / "temp_prompt_dumps.txt"

PLACEHOLDER = "<PASTE CONTEXT PACK JSON HERE>"
REPLACEMENT_CHAR = "\uFFFD"
CONTEXT_PACK_MARKER = "### Context Pack"


def _strip_json_block(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


def is_empty_or_trivial(response_text: str | None) -> bool:
    cleaned = _strip_json_block(response_text or "")
    if not cleaned:
        return True
    if cleaned in ("{}", "null", "[]"):
        return True
    try:
        data = json.loads(cleaned)
        return isinstance(data, dict) and len(data) == 0
    except Exception:
        return False


def extract_context_pack_from_user_prompt(user_prompt: str) -> str:
    """Return the JSON blob after '### Context Pack' in user_prompt, or ''."""
    idx = user_prompt.find(CONTEXT_PACK_MARKER)
    if idx == -1:
        return ""
    start = idx + len(CONTEXT_PACK_MARKER)
    return user_prompt[start:].lstrip()


def parse_context_pack(pack_str: str) -> tuple[dict | None, str | None]:
    """Try to parse context pack JSON. Return (parsed_dict, None) or (None, error_msg)."""
    pack_str = pack_str.strip()
    if not pack_str:
        return None, "Context pack section empty"
    try:
        data = json.loads(pack_str)
        if not isinstance(data, dict):
            return None, "Context pack is not a JSON object"
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {e}"


def check_prompt_build(system_prompt: str, user_prompt: str) -> list[str]:
    """Return list of detected issues in prompt building (empty = no issues)."""
    issues = []

    # 1. Leftover placeholder
    if PLACEHOLDER in user_prompt:
        issues.append("USER prompt still contains placeholder: <PASTE CONTEXT PACK JSON HERE>")

    # 2. Context pack extraction and parse
    pack_str = extract_context_pack_from_user_prompt(user_prompt)
    if not pack_str:
        issues.append("USER prompt has no '### Context Pack' section or nothing after it")
    else:
        pack, err = parse_context_pack(pack_str)
        if err:
            issues.append(f"Context pack JSON invalid: {err}")
            # Heuristic: unbalanced braces
            if pack_str.count("{") != pack_str.count("}"):
                issues.append("Context pack: unbalanced curly braces")
        else:
            for key in ("pass_kind", "seed", "same_type_neighbors", "cross_type"):
                if key not in pack:
                    issues.append(f"Context pack missing key: {key}")
            if pack and "seed" in pack and isinstance(pack["seed"], dict):
                seed = pack["seed"]
                if "claim_id" not in seed:
                    issues.append("Context pack seed missing claim_id")

    # 3. System prompt expected structure
    if "## Output schema" not in system_prompt:
        issues.append("System prompt missing '## Output schema' section")
    if "decision" not in system_prompt and '"decision"' not in system_prompt:
        issues.append("System prompt missing 'decision' (output schema may be incomplete)")
    if "seed_claim_id" not in system_prompt and '"seed_claim_id"' not in system_prompt:
        issues.append("System prompt missing 'seed_claim_id' in schema")

    # 4. Problematic characters
    if REPLACEMENT_CHAR in system_prompt or REPLACEMENT_CHAR in user_prompt:
        issues.append("Replacement character (U+FFFD) found in prompt")
    for label, s in [("system", system_prompt), ("user", user_prompt)]:
        for i, c in enumerate(s):
            if ord(c) < 32 and c not in "\n\r\t":
                issues.append(f"Control character in {label} prompt at position {i}: ord={ord(c)}")
                break

    # 5. Backslash-newline in context pack (can break some parsers)
    if "\\\n" in pack_str or '\\\r' in pack_str:
        issues.append("Context pack contains backslash-newline sequences")

    return issues


def main() -> None:
    init_db()
    with session_scope() as session:
        stmt = select(LlmCall).where(LlmCall.created_at >= CUTOFF).order_by(LlmCall.created_at)
        calls = list(session.execute(stmt).scalars().all())
        # Copy needed attributes while session is active (objects detach after exit)
        rows = []
        for c in calls:
            rt = c.response_text
            rows.append({
                "id": c.id,
                "run_id": c.run_id,
                "created_at": c.created_at,
                "status": c.status,
                "error_message": c.error_message,
                "request_json": c.request_json,
                "response_text": rt,
                "response_json": c.response_json,
            })

    valid = []
    empty = []
    other = []

    for c in rows:
        rt = c["response_text"]
        is_empty = c["status"] == "PARSE_FAILED" and (
            (c["error_message"] and "empty or trivial" in (c["error_message"] or "").lower())
            or is_empty_or_trivial(rt or "")
        )
        is_valid = c["status"] == "SUCCESS" and c["response_json"] and not is_empty_or_trivial(rt or "")

        try:
            req = json.loads(c["request_json"]) if c["request_json"] else {}
        except Exception:
            req = {}

        system_prompt = req.get("system_prompt") or ""
        user_prompt = req.get("user_prompt") or ""
        seed_id = req.get("seed_claim_id", "")
        pass_kind = req.get("pass_kind", "")

        build_issues = check_prompt_build(system_prompt, user_prompt)

        rec = {
            "id": c["id"],
            "run_id": c["run_id"],
            "created_at": str(c["created_at"]),
            "status": c["status"],
            "error_message": (c["error_message"] or "")[:200],
            "pass_kind": pass_kind,
            "seed_claim_id": seed_id,
            "len_system": len(system_prompt),
            "len_user": len(user_prompt),
            "has_chunk_excerpt": '"chunk_excerpt":' in user_prompt and '"chunk_excerpt": null' not in user_prompt,
            "has_projectflow_quoted": 'ProjectFlow Pro' in user_prompt and ('\\"' in user_prompt or '"ProjectFlow' in user_prompt),
            "response_text_preview": (rt or "")[:120].replace("\n", " "),
            "build_issues": build_issues,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }

        if is_valid:
            valid.append(rec)
        elif is_empty:
            empty.append(rec)
        else:
            other.append(rec)

    # Write report
    lines = [
        f"llm_calls with created_at >= {CUTOFF}",
        f"Total: {len(calls)}",
        f"Valid (SUCCESS + non-empty response): {len(valid)}",
        f"Empty (PARSE_FAILED / empty or trivial): {len(empty)}",
        f"Other: {len(other)}",
        "",
        "=" * 60,
        "VALID PROMPTS (summary)",
        "=" * 60,
    ]

    if valid:
        len_sys = [r["len_system"] for r in valid]
        len_usr = [r["len_user"] for r in valid]
        has_excerpt = sum(1 for r in valid if r["has_chunk_excerpt"])
        has_pf = sum(1 for r in valid if r["has_projectflow_quoted"])
        lines.append(f"  len_system: min={min(len_sys)} max={max(len_sys)} avg={sum(len_sys)/len(len_sys):.0f}")
        lines.append(f"  len_user:   min={min(len_usr)} max={max(len_usr)} avg={sum(len_usr)/len(len_usr):.0f}")
        lines.append(f"  has chunk_excerpt (non-null): {has_excerpt}/{len(valid)}")
        lines.append(f"  has 'ProjectFlow Pro' (quoted): {has_pf}/{len(valid)}")
        lines.append("")
        for r in valid[:15]:
            lines.append(f"  {r['created_at']} | {r['pass_kind']} | {r['seed_claim_id'][:8]}... | sys={r['len_system']} user={r['len_user']} | excerpt={r['has_chunk_excerpt']} | pf_quoted={r['has_projectflow_quoted']}")
        if len(valid) > 15:
            lines.append(f"  ... and {len(valid) - 15} more")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.extend([
        "=" * 60,
        "EMPTY PROMPTS (summary)",
        "=" * 60,
    ])
    if empty:
        len_sys = [r["len_system"] for r in empty]
        len_usr = [r["len_user"] for r in empty]
        has_excerpt = sum(1 for r in empty if r["has_chunk_excerpt"])
        has_pf = sum(1 for r in empty if r["has_projectflow_quoted"])
        lines.append(f"  len_system: min={min(len_sys)} max={max(len_sys)} avg={sum(len_sys)/len(len_sys):.0f}")
        lines.append(f"  len_user:   min={min(len_usr)} max={max(len_usr)} avg={sum(len_usr)/len(len_usr):.0f}")
        lines.append(f"  has chunk_excerpt (non-null): {has_excerpt}/{len(empty)}")
        lines.append(f"  has 'ProjectFlow Pro' (quoted): {has_pf}/{len(empty)}")
        lines.append("")
        for r in empty[:20]:
            lines.append(f"  {r['created_at']} | {r['pass_kind']} | {r['seed_claim_id'][:8]}... | sys={r['len_system']} user={r['len_user']} | excerpt={r['has_chunk_excerpt']} | pf_quoted={r['has_projectflow_quoted']}")
        if len(empty) > 20:
            lines.append(f"  ... and {len(empty) - 20} more")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.extend([
        "=" * 60,
        "OTHER (parse failed but not empty, or other status)",
        "=" * 60,
    ])
    for r in other[:10]:
        lines.append(f"  {r['created_at']} | {r['status']} | {r['pass_kind']} | {r['seed_claim_id'][:8]}... | {r['error_message'][:80]}")
    if len(other) > 10:
        lines.append(f"  ... and {len(other) - 10} more")

    # Prompt build errors (any call with build_issues)
    all_with_issues = [r for r in valid + empty + other if r.get("build_issues")]
    lines.extend([
        "",
        "=" * 60,
        "PROMPT BUILD ERRORS (analysis of prompt text)",
        "=" * 60,
    ])
    if not all_with_issues:
        lines.append("  No structural errors detected in any prompt.")
        lines.append("  (Checked: placeholder left in, context pack JSON parseable, required keys,")
        lines.append("   output schema present, no U+FFFD, no control chars, no backslash-newline)")
    else:
        lines.append(f"  {len(all_with_issues)} call(s) have one or more potential build issues:")
        for r in all_with_issues:
            lines.append(f"  --- {r['created_at']} | {r['status']} | {r['pass_kind']} | {r['seed_claim_id'][:8]}... ---")
            for issue in r["build_issues"]:
                lines.append(f"    - {issue}")
        lines.append("")
        # Summary of issue types
        all_issues = []
        for r in all_with_issues:
            all_issues.extend(r["build_issues"])
        for issue_type, count in Counter(all_issues).most_common():
            lines.append(f"  [{count}x] {issue_type}")

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")

    # Dump full prompts for one valid and one empty (for manual inspection)
    dump_lines = [
        "Full prompt dumps for manual analysis of prompt building.",
        "Compare VALID vs EMPTY to spot differences.",
        "",
    ]
    if valid:
        r = valid[0]
        dump_lines.extend([
            "=" * 60,
            f"VALID (seed={r['seed_claim_id']}, created_at={r['created_at']})",
            "=" * 60,
            "",
            "--- USER PROMPT (first 8000 chars) ---",
            (r["user_prompt"] or "")[:8000],
            "",
            "--- SYSTEM PROMPT (first 3000 chars) ---",
            (r["system_prompt"] or "")[:3000],
            "",
        ])
    if empty:
        r = empty[0]
        dump_lines.extend([
            "=" * 60,
            f"EMPTY (seed={r['seed_claim_id']}, created_at={r['created_at']})",
            "=" * 60,
            "",
            "--- USER PROMPT (first 8000 chars) ---",
            (r["user_prompt"] or "")[:8000],
            "",
            "--- SYSTEM PROMPT (first 3000 chars) ---",
            (r["system_prompt"] or "")[:3000],
            "",
        ])
    DUMPS_FILE.write_text("\n".join(dump_lines), encoding="utf-8")
    print(f"Wrote {DUMPS_FILE}")


if __name__ == "__main__":
    main()
