# AI Stack: LlamaIndex, LlamaParse/Hub, LangChain, Langfuse, LocalAI, OpenWebUI

## Core recommendations
- Retrieval & KG orchestration: **LlamaIndex** (primary). Use PGVector + Neo4j stores.
- Parsing: **LlamaParse** for PDFs/complex docs; **LlamaHub** for loaders as needed.
- Workflow framework: **LangChain** optional; good for toolchains/agents, but avoid duplicating LlamaIndex unless a specific LC integration is required.
- Telemetry/analytics: **Langfuse** optional; adds tracing, evals, PII-handling. Included in `compose.ai.yml`.
- Local inference: **LocalAI** optional; OpenAI-compatible endpoint for on-prem models. Paired with **OpenWebUI** for operator UI.

## When to include
- Include LlamaIndex now (pip dependencies in app/worker images):
  - `llama-index` core
  - `llama-index-vector-stores-postgres` (pgvector)
  - `llama-index-graph-stores-neo4j`
  - `llama-parse` (if needed for PDFs)
  - `llama-hub` (selected loaders)

- Include Langfuse if you want run-time observability and experiment tracking; point it at Postgres.

- Include LocalAI/OpenWebUI if you need on-prem inference and a simple UI for testing; otherwise keep them off.

## Trade-offs
- LlamaIndex vs LangChain: LlamaIndex offers first-class PGVector + Neo4j graph store with hybrid engines out of the box. LangChain excels at tool abstractions and agent frameworks. You can use both, but start with one to reduce complexity.
- LocalAI: Great for air-gapped or cost control, but ensure model compatibility and hardware tuning (AVX, RAM).

