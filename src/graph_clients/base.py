from __future__ import annotations
from typing import Any, Dict, List, Optional
import os


class GraphBackend:
    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None, mode: str = "read") -> List[Dict[str, Any]]:
        raise NotImplementedError

    def test_connection(self) -> bool:
        raise NotImplementedError

    def insights(self) -> Dict[str, Any]:
        raise NotImplementedError


class Neo4jBackend(GraphBackend):
    def __init__(self, uri: str, user: str, password: str):
        from neo4j import GraphDatabase
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None, mode: str = "read") -> List[Dict[str, Any]]:
        with self._driver.session() as sess:
            if mode == "write":
                res = sess.run(query, **(params or {}))
            else:
                res = sess.run(query, **(params or {}))
            return [r.data() for r in res]

    def test_connection(self) -> bool:
        try:
            with self._driver.session() as sess:
                sess.run("RETURN 1 AS ok").single()
            return True
        except Exception:
            return False

    def insights(self) -> Dict[str, Any]:
        with self._driver.session() as sess:
            label_counts = sess.run("MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS cnt ORDER BY cnt DESC LIMIT 20").data()
            edge_counts = sess.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS cnt ORDER BY cnt DESC LIMIT 20").data()
            top_degree = sess.run("MATCH (n) RETURN n.id AS id, labels(n) AS labels, size((n)--()) AS deg ORDER BY deg DESC LIMIT 20").data()
            dangling = sess.run("MATCH (n) WHERE size((n)--())=0 RETURN labels(n) AS labels, n.id AS id LIMIT 50").data()
        return {"labels": label_counts, "edges": edge_counts, "top_degree": top_degree, "dangling": dangling}


class NebulaBackend(GraphBackend):
    def __init__(self, host: str, port: int, user: str, password: str, space: str):
        from nebula3.gclient.net import ConnectionPool
        from nebula3.Config import Config
        self.space = space
        config = Config()
        self.pool = ConnectionPool()
        self.pool.init([(host, port)], config)
        self.user = user
        self.password = password

    def _session(self):
        sess = self.pool.get_session(self.user, self.password)
        if self.space:
            sess.execute(f"USE {self.space}")
        return sess

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None, mode: str = "read") -> List[Dict[str, Any]]:
        # params not supported in raw NGQL
        from nebula3.Exception import IOErrorException
        sess = self._session()
        try:
            res = sess.execute(query)
            if not res.is_succeeded():
                raise RuntimeError(res.error_msg())
            col_names = res.keys()
            out = []
            for i in range(res.rows_size()):
                row = res.row_values(i)
                d = {}
                for idx, name in enumerate(col_names):
                    d[name] = row[idx].cast_to_string() if hasattr(row[idx], 'cast_to_string') else str(row[idx])
                out.append(d)
            return out
        finally:
            sess.release()

    def test_connection(self) -> bool:
        try:
            sess = self._session()
            r = sess.execute("SHOW SPACES")
            ok = r.is_succeeded()
            sess.release()
            return ok
        except Exception:
            return False

    def insights(self) -> Dict[str, Any]:
        sess = self._session()
        try:
            tags_res = sess.execute("SHOW TAGS")
            edges_res = sess.execute("SHOW EDGES")
            tags = [tags_res.row_values(i)[0].cast_to_string() for i in range(tags_res.rows_size())] if tags_res.is_succeeded() else []
            edges = [edges_res.row_values(i)[0].cast_to_string() for i in range(edges_res.rows_size())] if edges_res.is_succeeded() else []
            tag_counts = []
            for t in tags[:10]:
                r = sess.execute(f"MATCH (v:`{t}`) RETURN count(v) as cnt")
                cnt = r.row_values(0)[0].cast_to_string() if r.is_succeeded() and r.rows_size()>0 else '0'
                tag_counts.append({"tag": t, "count": int(cnt) if cnt.isdigit() else cnt})
            edge_counts = []
            for e in edges[:10]:
                r = sess.execute(f"MATCH ()-[r:`{e}`]->() RETURN count(r) as cnt")
                cnt = r.row_values(0)[0].cast_to_string() if r.is_succeeded() and r.rows_size()>0 else '0'
                edge_counts.append({"edge": e, "count": int(cnt) if cnt.isdigit() else cnt})
            return {"tags": tag_counts, "edges": edge_counts}
        finally:
            sess.release()


class TerminusBackend(GraphBackend):
    def __init__(self, server_url: str, db: str, user: str, password: str, token: Optional[str] = None):
        from terminusdb_client import WOQLClient
        self.client = WOQLClient(server_url)
        if token:
            self.client.connect(db=db, team=user, jwt_token=token)
        else:
            self.client.connect(db=db, team=user, key=password)

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None, mode: str = "read") -> List[Dict[str, Any]]:
        # Expect JSON‑WOQL or a string for future DSL support.
        if query.strip().startswith("{"):
            import json as _json
            woql = _json.loads(query)
            res = self.client.query(woql)
            return res.get('bindings', []) if isinstance(res, dict) else []
        raise NotImplementedError("Only JSON‑WOQL supported in this scaffold")

    def test_connection(self) -> bool:
        try:
            self.client.get_database(self.client.db())
            return True
        except Exception:
            return False

    def insights(self) -> Dict[str, Any]:
        from terminusdb_client import WOQLQuery as WQ
        out: Dict[str, Any] = {}
        try:
            # Triple count
            triple_q = WQ().triple("v:s","v:p","v:o").count("v:count").to_dict()
            tres = self.client.query(triple_q)
            tcount = 0
            if isinstance(tres, dict) and tres.get('bindings'):
                c = tres['bindings'][0].get('v:count')
                tcount = int(c) if isinstance(c, (int,float)) or (isinstance(c,str) and c.isdigit()) else 0
            out['triples'] = tcount
        except Exception:
            out['triples'] = None
        try:
            # Class counts (rdf:type)
            type_q = (WQ().triple("v:s","rdf:type","v:cls")
                      .group_by("v:cls", [WQ().count("v:c")], ["v:c"]) ).to_dict()
            res = self.client.query(type_q)
            classes = []
            if isinstance(res, dict):
                for b in res.get('bindings', [])[:20]:
                    classes.append({"class": b.get('v:cls'), "count": b.get('v:c')})
            out['classes'] = classes
        except Exception:
            out['classes'] = []
        return out


def select_backend(settings: Dict[str, Any], prefer: Optional[str] = None) -> GraphBackend:
    g = settings.get("graph_backends", {})
    default = g.get("default")
    if prefer:
        prefer_key = prefer.lower()
    else:
        prefer_key = default.lower() if isinstance(default, str) else None

    if prefer_key in {"nebula", "nebulagraph"} or (prefer_key is None and g.get("nebulagraph")):
        nb = settings.get("nebulagraph", {})
        return NebulaBackend(nb.get("host", "127.0.0.1"), int(nb.get("port", 9669)), nb.get("user", "root"), nb.get("password", ""), nb.get("space", ""))
    if prefer_key in {"terminus", "terminusdb"} or (prefer_key is None and g.get("terminusdb")):
        tb = settings.get("terminusdb", {})
        return TerminusBackend(tb.get("server_url", "http://127.0.0.1:6363"), tb.get("db", "admin"), tb.get("user", "admin"), tb.get("password", ""), tb.get("token", ""))
    # default neo4j
    neo = settings.get("mcp_api", {}).get("neo4j", {})
    return Neo4jBackend(neo.get("uri", os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")), neo.get("user", os.getenv("NEO4J_USER", "neo4j")), neo.get("password", os.getenv("NEO4J_PASSWORD", "")))
