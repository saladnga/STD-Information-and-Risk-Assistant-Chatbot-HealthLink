#!/usr/bin/env python3
"""
Re-upload every PDF in app/data/pdf/ to a running backend's /rag/upload.

Ingestion only ever happens through that endpoint - never automatically on startup - so a fresh environment (a new Supabase project, or a Render
service whose database was never seeded) starts with an empty knowledge base until this is run against it. Use this whenever /rag/stats shows 0 chunks/documents but app/data/pdf/ isn't empty.

/rag/upload now requires a logged-in account (see routers/rag.py), so this logs in first with real credentials, same login pattern test_chat_latency.py uses.

Usage:
    cd backend
    ../.venv/bin/python reingest_pdfs.py --url https://your-app.onrender.com \\
        --email you@example.com --password '...'
"""

import sys
import os
import json
import glob
import uuid
import argparse
import urllib.request
import urllib.error


def login(base_url: str, email: str, password: str) -> str:
    req = urllib.request.Request(
        f"{base_url}/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError as e:
        print(f"Login failed ({e.code}): {e.read().decode()}")
        sys.exit(1)


def upload_pdf(base_url: str, token: str, pdf_path: str) -> dict:
    """Hand-rolled multipart body - avoids adding `requests` as a dependency just for this one-off admin script."""
    boundary = uuid.uuid4().hex
    filename = os.path.basename(pdf_path)
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{base_url}/rag/upload",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"status": "error", "detail": f"{e.code}: {e.read().decode()}"}


def main():
    parser = argparse.ArgumentParser(
        description="Re-ingest every PDF in app/data/pdf/ into a running backend"
    )
    parser.add_argument(
        "--url", required=True, help="Backend base URL, e.g. https://your-app.onrender.com"
    )
    parser.add_argument("--email", required=True, help="An existing account's email")
    parser.add_argument("--password", required=True, help="That account's password")
    args = parser.parse_args()

    pdf_dir = os.path.join(os.path.dirname(__file__), "app", "data", "pdf")
    pdfs = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}")
        sys.exit(1)

    print(f"Found {len(pdfs)} PDFs. Logging in to {args.url}...")
    token = login(args.url, args.email, args.password)

    failures = 0
    for pdf_path in pdfs:
        filename = os.path.basename(pdf_path)
        print(f"Uploading: {filename} ...", end=" ", flush=True)
        result = upload_pdf(args.url, token, pdf_path)
        if result.get("status") == "success":
            print(f"OK - {result.get('chunks_ingested')} chunks")
        else:
            failures += 1
            print(f"FAILED - {result}")

    print(f"\nDone. Check {args.url}/rag/stats to confirm the new totals.")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
