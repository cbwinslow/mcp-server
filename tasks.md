Project tasks — MCP ingest & repo harvesting

High level:

- [ ] Pin project to Python 3.10 (done: `.python-version`)
- [ ] Use `uv` (Astra) as the dependency manager; document install & usage
- [ ] Gather/populate GitHub projects: Continue, CodeGPT, Graphite, Ottoman Agents, LangChain, LangGraph, LangSmith, Langfuse, LocalAI/Ollama, Linear/Jira/Confluence connectors
- [ ] Mirror or import permissively-licensed repos into `imports/` where appropriate
- [ ] Scrape or use pigsty CLI to gather scripts into `tools/pigsty/`
- [ ] Add knowledge-graph-capable projects and agent templates to `imports/agents/`
- [ ] Add legal doc analysis tools and parsers to `imports/legal_tools/`
- [ ] Add embeddings model utilities and adapters to `mcp_ingest/embeddings_adapters/`
- [ ] Create a `deploy/` plan to run multiple MCP servers in Docker or Kubernetes
- [ ] Setup Confluence/Jira/Linear integrations and push docs repo to each platform
- [ ] Evaluate local AI runtimes: Ollama, LocalAI, etc., and add to `deploy/` with scripts
- [ ] Create a small knowledge graph PoC using Neo4j or RDF store

Disk cleanup & backups
- [ ] Run `cleanup/cleanup_desktop_and_kernels.sh` (dry-run) and review packages to remove
- [ ] Use `tools/backup_rsync.sh` to snapshot large folders to external disk or network mount
- [ ] Use `tools/git_repo_backup.py` to scan and push all local git repos to GitHub (dry-run then push)


Immediate next actions:
1. I will harvest top GitHub repos by topic and add them to `imports/` (or list them if license prevents mirroring).
2. I will fetch pigsty scripts (via CLI if available) into `tools/pigsty/`.
3. I will add a short `tools/README.md` describing steps to run uv/astra and bootstrap the project.
