#!/usr/bin/env python3
"""
Initialize a minimal TerminusDB schema for Repo, File, Chunk, Embedding.
Keeps configuration separate; this is optional and idempotent best‑effort.
"""

import os
from terminusdb_client import WOQLClient


def init_schema():
    url = os.getenv('TERMINUSDB_URL', 'http://127.0.0.1:6363')
    db = os.getenv('TERMINUSDB_DB', 'admin')
    user = os.getenv('TERMINUSDB_USER', 'admin')
    key = os.getenv('TERMINUSDB_PASSWORD', '')
    token = os.getenv('TERMINUSDB_TOKEN', '')

    client = WOQLClient(url)
    if token:
        client.connect(db=db, team=user, jwt_token=token)
    else:
        client.connect(db=db, team=user, key=key)

    schema = {
        '@type': 'Class',
        '@id': 'Repo',
        '@key': {'@type': 'Random'},
        'name': {'@type': 'xsd:string'},
        'owner': {'@type': 'xsd:string'},
        'url': {'@type': 'xsd:string'},
        'language': {'@type': 'xsd:string', '@cardinality': 'OneOrNone'},
        'stars': {'@type': 'xsd:integer'},
        'forks': {'@type': 'xsd:integer'},
    }
    file_schema = {
        '@type': 'Class',
        '@id': 'File',
        '@key': {'@type': 'Random'},
        'path': {'@type': 'xsd:string'},
        'repo': {'@type': 'Repo', '@cardinality': 'OneOrNone'},
    }
    chunk_schema = {
        '@type': 'Class',
        '@id': 'Chunk',
        '@key': {'@type': 'Random'},
        'index': {'@type': 'xsd:integer'},
        'text': {'@type': 'xsd:string'},
        'file': {'@type': 'File', '@cardinality': 'OneOrNone'},
    }
    embedding_schema = {
        '@type': 'Class',
        '@id': 'Embedding',
        '@key': {'@type': 'Random'},
        'model': {'@type': 'xsd:string'},
        'vector': {'@type': 'xsd:string'},
        'chunk': {'@type': 'Chunk', '@cardinality': 'OneOrNone'},
        'repo': {'@type': 'Repo', '@cardinality': 'OneOrNone'},
    }

    # Upsert schemas
    for doc in (schema, file_schema, chunk_schema, embedding_schema):
        try:
            client.update_document(doc)
        except Exception:
            client.insert_document(doc)

    return {'status': 'success', 'classes': ['Repo', 'File', 'Chunk', 'Embedding']}


if __name__ == '__main__':
    print(init_schema())

