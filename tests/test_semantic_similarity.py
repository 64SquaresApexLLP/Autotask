#!/usr/bin/env python3
"""
Test suite for semantic similar-ticket search (Snowflake Cortex).

Run this while `backend.main:app` (uvicorn) is running on http://localhost:8000.

Context: SNOWFLAKE.CORTEX.AI_SIMILARITY() is NOT available on this Snowflake
account ("Unknown user-defined function" - SQL compilation error 002141). The
implementation therefore uses Cortex embeddings + VECTOR_COSINE_SIMILARITY
(EMBED_TEXT_768, model 'e5-base-v2') with a keyword (ILIKE) fallback.

Validates:
- Cortex embedding / vector-cosine functions are available on this account
- Active code paths no longer call the unavailable AI_SIMILARITY function
- The live similar-tickets endpoint responds without a server error
- The chat endpoint still answers after gathering similar-ticket context
"""

import os
import sys
import time
import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)

BASE_URL = "http://localhost:8000"
CHATBOT_URL = f"{BASE_URL}/chatbot"
REQUEST_TIMEOUT = 120

PASS = 0
FAIL = 0


def report(test_name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  OK  {test_name}")
    else:
        FAIL += 1
        print(f"  X   {test_name} | {detail}")


def test_vector_functions_available():
    """EMBED_TEXT_768 + VECTOR_COSINE_SIMILARITY must work (AI_SIMILARITY does not)."""
    print("test_vector_functions_available")
    try:
        from chatbot.database import engine

        raw = engine.raw_connection()
        try:
            cur = raw.cursor()
            cur.execute(
                "SELECT VECTOR_COSINE_SIMILARITY("
                "SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', 'printer not working')::VECTOR(FLOAT, 768), "
                "SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', 'printer is broken')::VECTOR(FLOAT, 768))"
            )
            score_related = cur.fetchone()[0]
            cur.execute(
                "SELECT VECTOR_COSINE_SIMILARITY("
                "SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', 'printer not working')::VECTOR(FLOAT, 768), "
                "SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', 'quarterly budget spreadsheet')::VECTOR(FLOAT, 768))"
            )
            score_unrelated = cur.fetchone()[0]
            cur.close()
            report(
                "cortex vector similarity works (related > 0.5)",
                isinstance(score_related, (int, float)) and score_related > 0.5,
                f"score={score_related}",
            )
            report(
                "vector scoring is semantic (related > unrelated)",
                score_related > score_unrelated,
                f"related={score_related} unrelated={score_unrelated}",
            )
        finally:
            raw.close()
    except Exception as e:
        report("cortex vector similarity works (related > 0.5)", False, str(e))
        report("vector scoring is semantic (related > unrelated)", False, str(e))


def test_no_ai_similarity_in_active_code():
    """Active search paths must not call the unavailable AI_SIMILARITY function."""
    print("test_no_ai_similarity_in_active_code")
    root = os.path.join(os.path.dirname(__file__), "..")
    active_files = [
        os.path.join(root, "backend", "chatbot", "simple_router.py"),
        os.path.join(root, "src", "agents", "intake_agent.py"),
    ]
    for path in active_files:
        name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            report(f"no live AI_SIMILARITY call in {name}", False, str(e))
            continue
        # Flag actual SQL invocations - the call starts the statement line.
        # Docstring/comment notes about AI_SIMILARITY don't start a line with it.
        live_call = any(
            line.strip().startswith(("AI_SIMILARITY(", "SNOWFLAKE.CORTEX.AI_SIMILARITY("))
            for line in content.splitlines()
        )
        report(f"no live AI_SIMILARITY call in {name}", not live_call,
               "still calls SNOWFLAKE.CORTEX.AI_SIMILARITY")
        report(f"uses vector embeddings in {name}",
               "VECTOR_COSINE_SIMILARITY" in content and "EMBED_TEXT_768" in content,
               "vector approach missing")


def test_similar_tickets_endpoint():
    """Endpoint must respond cleanly (200, or 404 when ticket is unknown) - never
    a 500 caused by the SQL compilation error."""
    print("test_similar_tickets_endpoint")
    try:
        r = requests.get(f"{CHATBOT_URL}/tickets/similar/T001", timeout=60)
        ok = r.status_code in (200, 404)
        report("similar-tickets endpoint responds cleanly", ok,
               f"status={r.status_code} body={r.text[:120]}")
        if r.status_code == 200:
            report("similar-tickets returns a list", isinstance(r.json(), list), r.text[:120])
    except Exception as e:
        report("similar-tickets endpoint responds cleanly", False, str(e))


def test_chat_after_context_gathering():
    """A technical prompt gathers ticket context (semantic search) and still answers."""
    print("test_chat_after_context_gathering")
    payload = {
        "message": "My laptop touchpad is unresponsive and behaves erratically",
        "session_id": f"semtest_{int(time.time())}",
    }
    try:
        r = requests.post(f"{CHATBOT_URL}/chat", json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            report("chat answers with context gathering", False, f"status={r.status_code}")
            return
        resp = r.json().get("response", "")
        report("chat answers with context gathering", len(resp) > 60, resp[:120])
    except Exception as e:
        report("chat answers with context gathering", False, str(e))


def main():
    print("Semantic Similarity (Cortex embeddings) Test Suite")
    print("=" * 58)
    test_vector_functions_available()
    test_no_ai_similarity_in_active_code()
    test_similar_tickets_endpoint()
    test_chat_after_context_gathering()
    print("=" * 58)
    print(f"Results: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
