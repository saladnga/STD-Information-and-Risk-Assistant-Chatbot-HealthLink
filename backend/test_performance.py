#!/usr/bin/env python3
"""
Performance benchmark for Troy HealthLink - prints real, measured numbers from your own running system, so anything you quote on a resume is a number you actually produced, not an estimate.

Measures three things:
1. Raw XGBoost inference speed - no network, just the model itself.
2. End-to-end /predict API latency - the real round trip a user experiences.
3. RAG retrieval latency (/rag/ask) - sequential and concurrent.

Usage:
    cd backend
    ../.venv/bin/python test_performance.py                      # local server on :8000
    ../.venv/bin/python test_performance.py --url https://your-app.onrender.com
    ../.venv/bin/python test_performance.py --n 50 --concurrency 20
"""

import sys
import os
import time
import json
import argparse
import statistics
import urllib.request
import concurrent.futures

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

SAMPLE_SYMPTOMS = [
    "yellow discharge, burning during urination",
    "painful sores, fever, swollen lymph nodes",
    "itching, thin discharge, fishy odor",
    "pelvic pain, spotting between periods",
    "no odor, mild discomfort, discharge for a few days",
    "sore throat, fatigue, swollen glands",
]

SAMPLE_RAG_QUESTIONS = [
    "What are the symptoms of chlamydia?",
    "How is gonorrhea treated?",
    "What is bacterial vaginosis?",
    "How does STI testing work?",
    "What is the treatment for herpes?",
]


def _stats(label: str, times_ms: list, failures: int, total: int):
    print(f"\n{label}")
    print(f"Requests: {total} ({failures} failed)")
    if not times_ms:
        print("No successful requests - is the server running at that URL?")
        return
    ordered = sorted(times_ms)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    print(f"Mean: {statistics.mean(times_ms):.1f} ms")
    print(f"Median: {statistics.median(times_ms):.1f} ms")
    print(f"P95: {p95:.1f} ms")
    print(f"Min/Max: {min(times_ms):.1f} / {max(times_ms):.1f} ms")


def benchmark_model_inference(n: int):
    """Raw model.predict_proba speed - no network, no server needed."""
    from model import load_model, process_text_to_feature

    model, label_encoder, feature_columns = load_model()
    if model is None:
        print("\nSkipping model inference benchmark - no trained model found.")
        return

    import pandas as pd

    rows = [
        process_text_to_feature(SAMPLE_SYMPTOMS[i % len(SAMPLE_SYMPTOMS)], feature_columns)
        for i in range(n)
    ]
    df = pd.DataFrame(rows, columns=feature_columns)

    # Warm up once (first call pays a one-off setup cost that isn't representative)
    model.predict_proba(df.iloc[:1])

    times_ms = []
    for i in range(n):
        start = time.perf_counter()
        model.predict_proba(df.iloc[[i]])
        times_ms.append((time.perf_counter() - start) * 1000)

    _stats(f"Raw XGBoost inference ({n} predictions, single-row batches)", times_ms, 0, n)
    print(f"Throughput: {1000 / statistics.mean(times_ms):.0f} predictions/sec (single-threaded)")


def _timed_post(url: str, payload: dict, timeout: int = 30):
    start = time.perf_counter()
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            ok = resp.status == 200
    except Exception:
        ok = False
    return (time.perf_counter() - start) * 1000, ok


def benchmark_endpoint_sequential(url: str, payloads: list, label: str):
    times_ms, failures = [], 0
    for payload in payloads:
        elapsed, ok = _timed_post(url, payload)
        if ok:
            times_ms.append(elapsed)
        else:
            failures += 1
    _stats(label, times_ms, failures, len(payloads))
    return times_ms


def benchmark_endpoint_concurrent(url: str, payloads: list, label: str, concurrency: int):
    start_all = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda p: _timed_post(url, p), payloads))
    total_elapsed = time.perf_counter() - start_all

    times_ms = [t for t, ok in results if ok]
    failures = sum(1 for _, ok in results if not ok)
    _stats(label, times_ms, failures, len(payloads))
    if total_elapsed > 0:
        print(f"Throughput: {len(payloads) / total_elapsed:.1f} requests/sec at concurrency={concurrency}")


def main():
    parser = argparse.ArgumentParser(description="Troy HealthLink performance benchmark")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--n", type=int, default=30, help="Requests per benchmark")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent workers for the load test")
    parser.add_argument("--skip-model", action="store_true", help="Skip the direct model-inference benchmark")
    args = parser.parse_args()

    print("=" * 64)
    print(f"Troy HealthLink Performance Benchmark")
    print(f"Target: {args.url}   Requests per test: {args.n}")
    print("=" * 64)

    if not args.skip_model:
        benchmark_model_inference(args.n)

    predict_payloads = [
        {"text": SAMPLE_SYMPTOMS[i % len(SAMPLE_SYMPTOMS)]} for i in range(args.n)
    ]
    benchmark_endpoint_sequential(
        f"{args.url}/predict", predict_payloads, "POST /predict (sequential, end-to-end)"
    )
    benchmark_endpoint_concurrent(
        f"{args.url}/predict",
        predict_payloads,
        f"POST /predict (concurrent x{args.concurrency})",
        args.concurrency,
    )

    rag_payloads = [
        {"question": SAMPLE_RAG_QUESTIONS[i % len(SAMPLE_RAG_QUESTIONS)], "max_results": 5}
        for i in range(args.n)
    ]
    benchmark_endpoint_sequential(
        f"{args.url}/rag/ask", rag_payloads, "POST /rag/ask (sequential, includes OpenAI call)"
    )

    print("\n" + "=" * 64)
    print("Done. These numbers are only valid for the machine/instance you ran")
    print("them against right now - re-run before quoting a number anywhere,")
    print("and note whether it was local or the deployed (often colder/slower) instance.")
    print("=" * 64)


if __name__ == "__main__":
    main()
