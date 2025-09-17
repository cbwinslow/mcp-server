#!/usr/bin/env python3
"""
Code → Knowledge Graph extraction tools for CrewAI.
PythonAstExtractorTool parses Python source into nodes/edges JSON suitable for kg_sync.
"""

import ast
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List

from crewai_tools import BaseTool


def _stable_id(kind: str, qualname: str) -> str:
    return f"{kind}:{hashlib.sha1(qualname.encode('utf-8')).hexdigest()[:16]}"


@dataclass
class Node:
    label: str
    props: Dict[str, Any]


@dataclass
class Edge:
    src: Dict[str, Any]
    dst: Dict[str, Any]
    type: str
    props: Dict[str, Any]


class PythonAstExtractorTool(BaseTool):
    """Extract classes, functions, methods, and imports from Python code into KG JSON.

    Inputs:
      - code: Python source code (str)
      - repo: optional repo name or id
      - path: file path hint
    Output: JSON {nodes:[...], edges:[...]}
    """

    name: str = "Python AST → KG"
    description: str = "Parse Python code into nodes/edges (Repository, File, Class, Method, Function, IMPORTS, DEFINES)."

    def _run(self, code: str, repo: str = "repo", path: str = "file.py") -> str:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return json.dumps({"status": "failed", "error": f"SyntaxError: {e}"})

        nodes: List[Node] = []
        edges: List[Edge] = []

        repo_id = _stable_id("Repository", repo)
        file_id = _stable_id("File", f"{repo}:{path}")
        nodes.append(Node("Repository", {"id": repo_id, "name": repo}))
        nodes.append(Node("File", {"id": file_id, "path": path, "repo": repo}))
        edges.append(Edge({"label": "Repository", "id": repo_id}, {"label": "File", "id": file_id}, "CONTAINS", {}))

        class_stack: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                qual = ".".join(class_stack + [node.name]) if class_stack else node.name
                cid = _stable_id("Class", f"{repo}:{path}:{qual}")
                nodes.append(Node("Class", {"id": cid, "name": node.name, "qualname": qual, "path": path}))
                edges.append(Edge({"label": "File", "id": file_id}, {"label": "Class", "id": cid}, "DEFINES", {}))
            elif isinstance(node, ast.FunctionDef):
                qual = ".".join(class_stack + [node.name]) if class_stack else node.name
                fid = _stable_id("Function", f"{repo}:{path}:{qual}")
                label = "Method" if class_stack else "Function"
                nodes.append(Node(label, {"id": fid, "name": node.name, "qualname": qual, "path": path}))
                edges.append(Edge({"label": "File", "id": file_id}, {"label": label, "id": fid}, "DEFINES", {}))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imp = alias.name
                    iid = _stable_id("Module", imp)
                    nodes.append(Node("Module", {"id": iid, "name": imp}))
                    edges.append(Edge({"label": "File", "id": file_id}, {"label": "Module", "id": iid}, "IMPORTS", {}))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                iid = _stable_id("Module", mod)
                nodes.append(Node("Module", {"id": iid, "name": mod}))
                edges.append(Edge({"label": "File", "id": file_id}, {"label": "Module", "id": iid}, "IMPORTS", {}))

        out = {
            "status": "success",
            "nodes": [
                {"label": n.label, "properties": n.props} for n in _dedupe_nodes(nodes)
            ],
            "edges": [
                {
                    "src": {"label": e.src.get("label"), "id": e.src.get("id")},
                    "dst": {"label": e.dst.get("label"), "id": e.dst.get("id")},
                    "type": e.type,
                    "properties": e.props,
                }
                for e in _dedupe_edges(edges)
            ],
        }
        return json.dumps(out, indent=2)


def _dedupe_nodes(nodes: List[Node]) -> List[Node]:
    seen = set()
    out = []
    for n in nodes:
        key = (n.label, n.props.get("id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def _dedupe_edges(edges: List[Edge]) -> List[Edge]:
    seen = set()
    out = []
    for e in edges:
        key = (e.src.get("id"), e.type, e.dst.get("id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out

