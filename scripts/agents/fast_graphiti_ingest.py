#!/usr/bin/env python3
import os
import json
from pathlib import Path
import sys
import requests

sys.path.append(str(Path(__file__).resolve().parents[2] / 'src'))

from crewai.crewai_agent import CrewAIAgentManager
from crewai.graphiti_wrapped_tools import CrawlToGraphitiEpisodesTool


def mcp_api_crawl(url: str, depth: int = 1, max_pages: int = 3) -> dict:
    base = os.getenv("MCP_API_BASE", "http://127.0.0.1:8000").rstrip("/")
    headers = {"Content-Type": "application/json"}
    jwt = os.getenv("MCP_JWT")
    if jwt:
        headers["Authorization"] = f"Bearer {jwt}"
    r = requests.post(f"{base}/crawl", json={"url": url, "depth": depth, "max_pages": max_pages}, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()


def write_episodes_from_crawl(crawl_payload: dict, group_id: str, batch_by_domain: bool = True, max_items: int = 20, body_chars: int = 3000) -> dict:
    tool = CrawlToGraphitiEpisodesTool()
    res = tool._run(
        crawl_json=json.dumps(crawl_payload),
        group_id=group_id or "default",
        max_items=max_items,
        batch_by_domain=batch_by_domain,
        body_chars=body_chars,
    )
    try:
        return json.loads(res)
    except Exception:
        return {"status": "unknown", "raw": res}


def run_verify_task() -> dict:
    cfg = str(Path(__file__).resolve().parents[2] / 'config' / 'crewai_graphiti.yaml')
    manager = CrewAIAgentManager(cfg)
    manager.create_agents()
    manager.create_tasks()
    # Only run the verification task to avoid LLM planning for crawl/write steps
    result = manager.run_specific_task("verify-ingest")
    return result


def main():
    targets_env = os.getenv("TARGET_URLS") or os.getenv("TARGET_URL")
    if not targets_env:
        print(json.dumps({"status": "error", "error": "TARGET_URLS or TARGET_URL not set"}, indent=2))
        sys.exit(1)
    targets = [t.strip() for t in targets_env.replace("\n", ",").split(",") if t.strip()]
    if not targets:
        print(json.dumps({"status": "error", "error": "No valid targets provided"}, indent=2))
        sys.exit(1)
    group = os.getenv("GROUP_ID", "default")

    try:
        all_results = []
        for target in targets:
            crawl = mcp_api_crawl(target, depth=int(os.getenv("CRAWL_DEPTH", "1")), max_pages=int(os.getenv("CRAWL_MAX_PAGES", "3")))
            write_res = write_episodes_from_crawl(
                crawl,
                group_id=group,
                batch_by_domain=os.getenv("BATCH_BY_DOMAIN", "true").lower() in {"1","true","yes"},
                max_items=int(os.getenv("MAX_ITEMS", "20")),
                body_chars=int(os.getenv("BODY_CHARS", "3000")),
            )
            all_results.append({"target": target, "result": write_res})
        verify_res = run_verify_task()
        print(json.dumps({"status": "success", "crawl_index": all_results, "verify": verify_res}, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
