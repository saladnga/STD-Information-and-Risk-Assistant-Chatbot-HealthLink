#!/usr/bin/env python3
"""
WebSocket chat latency benchmark - measures the actual product surface (the real-time streaming chat a user experiences), not just /predict or /rag/ask.

Requires a dedicated benchmark test account (see TODO.md Part 1) with BENCHMARK_TEST_EMAIL / BENCHMARK_TEST_PASSWORD set in backend/app/.env.

Usage:
    cd backend
    ../.venv/bin/python test_chat_latency.py
    ../.venv/bin/python test_chat_latency.py --url http://127.0.0.1:8000 --n 10
"""

import sys
import os
import json
import time
import asyncio
import argparse
import urllib.request
import urllib.error

import websockets
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))
load_dotenv(os.path.join(os.path.dirname(__file__), "app", ".env"))

from test_performance import _stats

SAMPLE_MESSAGES = [
    "I've had yellow discharge and burning during urination for two days",
    "What are the symptoms of chlamydia?",
    "I'm experiencing pelvic pain and spotting between periods",
    "How is bacterial vaginosis treated?",
    "I have painful sores and swollen lymph nodes",
]


def login(base_url: str) -> str:
    """Log in with the dedicated benchmark account and return an access token."""
    email = os.getenv("BENCHMARK_TEST_EMAIL")
    password = os.getenv("BENCHMARK_TEST_PASSWORD")
    if not email or not password:
        print(
            "Missing BENCHMARK_TEST_EMAIL / BENCHMARK_TEST_PASSWORD in backend/app/.env"
        )
        sys.exit(1)

    req = urllib.request.Request(
        f"{base_url}/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        print(f"Login failed ({e.code}): {e.read().decode()}")
        sys.exit(1)



async def benchmark(ws_url: str, token: str, n: int):
    """One persistent connection, n messages sent sequentially - like a real conversation."""
    first_chunk_times, total_times, failures = [], [], 0
    messages = [SAMPLE_MESSAGES[i % len(SAMPLE_MESSAGES)] for i in range(n)]

    uri = f"{ws_url}/ws/chat?token={token}"
    async with websockets.connect(uri) as ws:
        await ws.recv()  # "__SESSION__:..." announcement - not a reply, discard

        for i, message in enumerate(messages):
            start = time.perf_counter()
            await ws.send(message)
            first_chunk_ms = None
            try:
                while True:
                    chunk = await asyncio.wait_for(ws.recv(), timeout=30)
                    if first_chunk_ms is None:
                        first_chunk_ms = (time.perf_counter() - start) * 1000
                    if chunk == "__DONE__":  # completion signal, matches frontend's own check
                        total_times.append((time.perf_counter() - start) * 1000)
                        first_chunk_times.append(first_chunk_ms)
                        break
            except Exception as e:
                print(f"  Exchange {i + 1} failed: {e}")
                failures += 1

    _stats(
        "WebSocket chat - time to first streamed chunk", first_chunk_times, failures, n
    )
    _stats("WebSocket chat - time to completion (full reply)", total_times, failures, n)


def main():
    parser = argparse.ArgumentParser(
        description="Troy HealthLink chat latency benchmark"
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000", help="Backend base URL"
    )
    parser.add_argument(
        "--n", type=int, default=10, help="Number of chat exchanges to measure"
    )
    args = parser.parse_args()

    ws_url = args.url.replace("http://", "ws://").replace("https://", "wss://")

    print("=" * 64)
    print("Troy HealthLink Chat Latency Benchmark")
    print(f"Target: {args.url}   Exchanges: {args.n}")
    print("=" * 64)

    token = login(args.url)
    asyncio.run(benchmark(ws_url, token, args.n))

    print("\n" + "=" * 64)
    print("Done. One persistent connection, messages sent sequentially in the")
    print("same session - includes a full OpenAI round trip per message.")
    print("Re-run before quoting a number anywhere.")
    print("=" * 64)


if __name__ == "__main__":
    main()
