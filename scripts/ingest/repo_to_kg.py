#!/usr/bin/env python3
import argparse
import os
import shutil
import tempfile
from pathlib import Path

from git import Repo

from src.crewai.code_kg_tools import PythonAstExtractorTool
from src.crewai.kg_tools import LlamaIndexGraphSyncTool


def clone_repo(url: str, dest: Path) -> Path:
    Repo.clone_from(url, dest)
    return dest


def walk_py_files(root: Path):
    for p in root.rglob("*.py"):
        if "/.venv/" in str(p) or "/venv/" in str(p):
            continue
        yield p


def run(repo_url: str, group: str | None = None, repo_name: str | None = None):
    tmp = Path(tempfile.mkdtemp(prefix="repo_kg_"))
    try:
        repo_path = clone_repo(repo_url, tmp / "repo")
        name = repo_name or Path(repo_url).stem
        ast_tool = PythonAstExtractorTool()
        sync_tool = LlamaIndexGraphSyncTool()

        total_nodes = 0
        total_edges = 0
        for f in walk_py_files(repo_path):
            try:
                code = f.read_text(encoding="utf-8", errors="ignore")
                res = ast_tool._run(code=code, repo=name, path=str(f.relative_to(repo_path)))
                payload = eval_json(res)
                nodes = payload.get("nodes", [])
                edges = payload.get("edges", [])
                if nodes or edges:
                    out = sync_tool._run(nodes=to_json(nodes), edges=to_json(edges))
                    total_nodes += len(nodes)
                    total_edges += len(edges)
            except Exception:
                continue
        print({"status": "success", "nodes": total_nodes, "edges": total_edges})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def to_json(obj) -> str:
    import json

    return json.dumps(obj)


def eval_json(s: str):
    import json

    try:
        return json.loads(s)
    except Exception:
        return {}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Clone a repo and index into Neo4j KG")
    ap.add_argument("repo_url")
    ap.add_argument("--group", default=None)
    ap.add_argument("--repo-name", default=None)
    args = ap.parse_args()
    run(args.repo_url, group=args.group, repo_name=args.repo_name)

