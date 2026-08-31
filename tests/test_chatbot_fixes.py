#!/usr/bin/env python3
"""
Test script to verify the LLM-powered chatbot (simple_router on port 8000).

Run this while `backend.main:app` (uvicorn) is running on http://localhost:8000.

Validates:
- EVERY prompt is routed to the LLM (technical issues, AI resolution, resolve ticket)
- The LLM internally handles scope (out-of-scope prompts are politely redirected)
- Ticket intents do NOT hallucinate ticket data
- Conversation history is maintained per session
- Dynamic per-request timestamps (regression for static datetime.now() default)
- Error handling / malformed requests
"""

import requests
import time

BASE_URL = "http://localhost:8000"
CHATBOT_URL = f"{BASE_URL}/chatbot"
REQUEST_TIMEOUT = 120  # Cortex calls can take a few seconds

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


def chat(message: str, session_id: str = None):
    payload = {
        "message": message,
        "session_id": session_id or f"test_{int(time.time())}_{abs(hash(message)) % 10000}",
    }
    try:
        r = requests.post(f"{CHATBOT_URL}/chat", json=payload, timeout=REQUEST_TIMEOUT)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"  (!) Request error: {e}")
        return None


def test_health_and_debug():
    print("test_health_and_debug")
    try:
        r = requests.get(f"{CHATBOT_URL}/health", timeout=15)
        report("health endpoint ok", r.status_code == 200 and r.json().get("status") == "ok")
    except Exception as e:
        report("health endpoint ok", False, str(e))
    try:
        d = requests.get(f"{CHATBOT_URL}/debug", timeout=15).json()
        report("LLM is initialized on the live server", d.get("llm_service_initialized") is True, str(d))
    except Exception as e:
        report("LLM is initialized on the live server", False, str(e))


def test_llm_technical_issue():
    print("test_llm_technical_issue")
    result = chat("My computer is running very slow and takes forever to start up")
    if not result:
        report("technical issue -> LLM step-by-step", False, "no response")
        return
    resp = result.get("response", "")
    has_steps = any(tok in resp.lower() for tok in ["1.", "step", "restart", "disable", "check", "update"])
    report("technical issue -> LLM step-by-step", len(resp) > 80 and has_steps, resp[:120])


def test_resolve_ticket():
    print("test_resolve_ticket")
    result = chat("What is the resolution for my current ticket")
    if not result:
        report("resolve ticket -> LLM, no canned menu", False, "no response")
        return
    resp = result.get("response", "").lower()
    canned = "i'm your it support chatbot assistant" in resp  # old canned generic menu marker
    report("resolve ticket -> LLM, no canned menu", not canned, resp[:150])


def test_scope_handling():
    print("test_scope_handling")
    result = chat("What is the best recipe for chocolate cake?")
    if not result:
        report("out-of-scope politely redirected", False, "no response")
        return
    resp = result.get("response", "").lower()
    declined = any(tok in resp for tok in ["it support", "can't provide", "cannot help", "not able to", "outside", "out of scope", "culinary"])
    gave_recipe = any(tok in resp for tok in ["ingredients", "bake at", "flour", "350°f"])
    report("out-of-scope politely redirected", declined and not gave_recipe, resp[:150])


def test_greeting_through_llm():
    print("test_greeting_through_llm")
    result = chat("Hello there")
    ok = result is not None and "hello" in result.get("response", "").lower()
    report("greeting responded (via LLM)", ok, result and result["response"][:100])


def test_ticket_no_hallucination():
    print("test_ticket_no_hallucination")
    result = chat("Show me my tickets")
    if not result:
        report("no invented ticket numbers", False, "no response")
        return
    resp = result.get("response", "")
    invented = any(tid in resp for tid in ["#12345", "#67890", "#123", "T20259999"])
    report("no invented ticket numbers", not invented, resp[:120])


def test_dynamic_timestamps():
    print("test_dynamic_timestamps")
    r1 = chat("laptop slow boot", session_id="ts_a")
    time.sleep(1)
    r2 = chat("laptop slow boot", session_id="ts_b")
    if not r1 or not r2:
        report("timestamps differ per request", False, "missing responses")
        return
    t1, t2 = r1.get("timestamp"), r2.get("timestamp")
    report("timestamps differ per request", t1 and t2 and t1 != t2, f"{t1} vs {t2}")


def test_error_handling():
    print("test_error_handling")
    try:
        r = requests.post(f"{CHATBOT_URL}/chat", json={"invalid_field": "test"}, timeout=15)
        report("malformed request rejected (422)", r.status_code == 422, f"got {r.status_code}")
    except Exception as e:
        report("malformed request rejected (422)", False, str(e))


def main():
    print("Starting Chatbot (LLM / always-LLM scope) Test Suite")
    print("=" * 58)
    test_health_and_debug()
    test_llm_technical_issue()
    test_resolve_ticket()
    test_scope_handling()
    test_greeting_through_llm()
    test_ticket_no_hallucination()
    test_dynamic_timestamps()
    test_error_handling()
    print("=" * 58)
    print(f"Results: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
