#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import List

import requests


def post(url: str, data: dict, headers: dict | None = None):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    r = requests.post(url, json=data, headers=h, timeout=120)
    r.raise_for_status()
    return r.json()


def normalize_texts(payload: dict) -> List[str]:
    # Try common fields from crawl results
    texts: List[str] = []
    if isinstance(payload, list):
        for item in payload:
            t = item.get("text") or item.get("content") or ""
            if t:
                texts.append(t)
        return texts
    if "texts" in payload and isinstance(payload["texts"], list):
        texts.extend([str(t) for t in payload["texts"] if t])
    if "results" in payload and isinstance(payload["results"], list):
        for it in payload["results"]:
            t = it.get("text") or it.get("content") or ""
            if t:
                texts.append(t)
    if not texts and "content" in payload:
        c = payload["content"]
        if isinstance(c, str):
            texts.append(c)
        elif isinstance(c, list):
            texts.extend([str(t) for t in c if t])
    return texts


def run():
    ap = argparse.ArgumentParser(description="Crawl URLs via MCP API proxy then index via LlamaIndex")
    ap.add_argument("urls", nargs="+", help="One or more URLs to crawl")
    ap.add_argument("--collection", default="mcp_chunks")
    ap.add_argument("--mcp", default=os.getenv("MCP_API_BASE", "http://127.0.0.1:8000"))
    ap.add_argument("--jwt", default=os.getenv("MCP_JWT", ""))
    args = ap.parse_args()

    headers = {}
    if args.jwt:
        headers["Authorization"] = f"Bearer {args.jwt}"

    total_indexed = 0
    for url in args.urls:
        try:
            crawl_res = post(f"{args.mcp}/crawl", {"url": url, "depth": 1, "max_pages": 3}, headers)
            texts = normalize_texts(crawl_res)
            if texts:
                idx_res = post(f"{args.mcp}/admin/index", {"texts": texts, "collection": args.collection}, headers)
                total_indexed += int(idx_res.get("indexed", 0))
        except Exception as e:
            print(json.dumps({"status": "failed", "url": url, "error": str(e)}))
    print(json.dumps({"status": "success", "indexed": total_indexed}))


if __name__ == "__main__":
    run()

