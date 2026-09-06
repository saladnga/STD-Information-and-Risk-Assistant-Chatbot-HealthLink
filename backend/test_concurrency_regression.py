#!/usr/bin/env python3
"""
Concurrency regression test for the shared-Supabase-client race condition.

Opens N authenticated WebSocket connections at once, each asking about a DIFFERENT real condition simultaneously, and checks every reply for:
  - mentioning the condition it actually asked about (catches cross-talk
    between concurrent sessions sharing state that should be per-request)
  - any citation actually matching a real ingested PDF, never a fabricated
    source name (the original bug this same race condition produced)

Requires the same benchmark account as test_chat_latency.py.

Usage:
    cd backend
    ../.venv/bin/python test_concurrency_regression.py
"""

import sys
import os
import re
import glob
import asyncio
import argparse
import websockets

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from test_chat_latency import login

PDF_DIR = os.path.join(os.path.dirname(__file__), "app", "data", "pdf")
REAL_PDF_NAMES = {
    os.path.basename(p) for p in glob.glob(os.path.join(PDF_DIR, "*.pdf"))
}

CITATION_BRACKET_RE = re.compile(r"\[Source:\s*([^\],]+)", re.IGNORECASE)
SOURCES_BLOCK_RE = re.compile(r"\*\*Sources:\*\*\s*\n((?:\d+\.\s.+\n?)+)")
SOURCES_LINE_RE = re.compile(r"^\d+\.\s+(.+?)\s*$", re.MULTILINE)

# (display label, keyword to look for in the reply, message that reliably leads the ML diagnosis flow to this condition - verified against the raw model directly with test_analysis_citations.py, independent of the LLM's own wording/turn-taking)
TEST_CASES = [
    (
        "chlamydia",
        "chlamydia",
        "I've had yellow discharge and burning during urination for two days",
    ),
    (
        "gonorrhea",
        "gonorrh",
        "I have thick discharge that's yellow-green, along with painful urination",
    ),
    (
        "bacterial vaginosis",
        "vaginosis",
        "I have a strong fishy odor, thin gray discharge, and some itching",
    ),
    (
        "herpes",
        "herpes",
        "I have painful blisters and sores, plus fever and swollen lymph nodes",
    ),
]


FOLLOW_UP = "That's all my symptoms. Please go ahead and analyze them now."


async def _recv_reply(ws) -> str:
    """Accumulate chunks until the completion sentinel, return the full reply."""
    reply = ""
    while True:
        chunk = await asyncio.wait_for(ws.recv(), timeout=45)
        if chunk == "__DONE__":
            return reply
        reply += chunk


async def ask_about_condition(ws_url: str, token: str, message: str) -> str:
    """
    Open a fresh connection and hold a short two-turn conversation.

    One message alone isn't enough: the system prompt (see
    build_system_prompt in chat_analysis.py) tells the model to ask
    clarifying questions until IT decides it has enough info before
    signalling "ANALYZE:" - that's an LLM judgment call, not a code branch,
    so a single message can't reliably reach the diagnosis path. A second
    "go ahead and analyze" turn - a completely normal thing a real user
    says - reliably pushes it there.
    """
    uri = f"{ws_url}/ws/chat?token={token}"
    async with websockets.connect(uri) as ws:
        announcement = await ws.recv()
        if not announcement.startswith("__SESSION__:"):
            # Session setup failed server-side (chat.py's except block sends the real reason as plain text before closing) - surface it instead of silently discarding it and reporting a generic connection error later.
            raise RuntimeError(f"session setup failed: {announcement}")
        await ws.send(message)
        await _recv_reply(ws)  # first turn - usually clarifying questions, discard
        await ws.send(FOLLOW_UP)
        return await _recv_reply(ws)


def check_reply(label: str, keyword: str, reply_text: str) -> list:
    """Return a list of problems found (empty list = clean pass)."""
    problems = []
    if not reply_text.strip():
        problems.append("empty reply")
        return problems

    if keyword.lower() not in reply_text.lower():
        problems.append(
            f"reply never mentions '{label}' - possible cross-talk between "
            f"concurrent sessions"
        )

    for match in CITATION_BRACKET_RE.finditer(reply_text):
        name = match.group(1).strip()
        if name not in REAL_PDF_NAMES and "knowledge base" not in name.lower():
            problems.append(f"fabricated bracket citation: [Source: {name}]")

    block_match = SOURCES_BLOCK_RE.search(reply_text)
    if block_match:
        for line_match in SOURCES_LINE_RE.finditer(block_match.group(1)):
            name = line_match.group(1).strip()
            if name not in REAL_PDF_NAMES:
                problems.append(f"fabricated Sources-block entry: {name}")

    return problems


async def run(ws_url: str, token: str):
    tasks = [
        ask_about_condition(ws_url, token, message) for _, _, message in TEST_CASES
    ]
    replies = await asyncio.gather(*tasks, return_exceptions=True)

    all_clean = True
    for (label, keyword, message), reply in zip(TEST_CASES, replies):
        print(f"\n--- {label} ---")
        print(f"Asked: {message}")
        if isinstance(reply, Exception):
            print(f"FAILED - connection error: {reply}")
            all_clean = False
            continue

        preview = reply.strip().replace("\n", " ")[:150]
        print(f"Reply preview: {preview}...")
        problems = check_reply(label, keyword, reply)
        if problems:
            all_clean = False
            for p in problems:
                print(f"FAIL - {p}")
        else:
            print("OK - mentions the right condition, no fabricated sources")

    return all_clean


def main():
    parser = argparse.ArgumentParser(
        description="Troy HealthLink concurrency regression test"
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000", help="Backend base URL"
    )
    args = parser.parse_args()

    ws_url = args.url.replace("http://", "ws://").replace("https://", "wss://")

    print("=" * 64)
    print("Troy HealthLink Concurrency Regression Test")
    print(f"Target: {args.url}   Concurrent connections: {len(TEST_CASES)}")
    print("Sending all messages at once, on different conditions, to")
    print("reproduce the exact scenario the shared-client race condition")
    print("(fixed this session) lived in.")
    print("=" * 64)

    token = login(args.url)
    all_clean = asyncio.run(run(ws_url, token))

    print("\n" + "=" * 64)
    if all_clean:
        print(
            "PASS - every concurrent session got its own correct, honestly-cited reply."
        )
    else:
        print("FAIL - see problems above. This is the race condition resurfacing.")
        sys.exit(1)
    print("=" * 64)


if __name__ == "__main__":
    main()
