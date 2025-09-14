# MCP Server Development Guide

## Architecture Overview
This is an MCP (Model Context Protocol) server focused on ingesting and harvesting GitHub repositories and tools. The codebase follows a modular structure:

- `mcp_ingest/` - Core MCP server implementation with crawler, database, embeddings, and extractor modules
- `tools/` - Utility scripts for GitHub harvesting, backups, and system management
- `cleanup/` - System cleanup and maintenance scripts
- `dotfiles/` - System configuration and setup scripts

### MCP Server Components
- `main.py` - Server entry point and MCP protocol handling
- `crawler.py` - GitHub repository discovery and crawling logic
- `extractor.py` - Content extraction from harvested repositories
- `embeddings.py` - Vector embeddings generation for semantic search
- `db.py` - Database operations and data persistence
- `tasks.py` - Background task processing and job management

### Data Pipeline
1. **Ingestion**: GitHub API crawling discovers repositories
2. **Extraction**: Source code and documentation are extracted
3. **Processing**: Content is processed and embeddings generated
4. **Storage**: Processed data stored in database for retrieval

## Development Workflows

### Quality Assurance
- **AutoClaude Checks**: Run automated quality checks via `.autoclaude/scripts/` before commits
- **Codacy Integration**: After ANY file edit, immediately run Codacy analysis with `codacy_cli_analyze` tool
- **Pre-commit Hooks**: All changes must pass pre-commit validation

### AutoClaude Workflow
AutoClaude provides automated quality gates with JSON output for CI/CD integration:

```bash
# Individual checks
.autoclaude/scripts/production-readiness.sh  # Checks for TODO/FIXME, debug code
.autoclaude/scripts/format-check.sh          # ESLint, code formatting validation
.autoclaude/scripts/test-check.sh            # Test execution and coverage
.autoclaude/scripts/build-check.sh           # Build validation across languages
.autoclaude/scripts/github-actions.sh        # GitHub Actions workflow validation
```

Each script outputs structured JSON with `passed`, `errors`, and `fixInstructions` fields.

### Build & Test
```bash
# Run all AutoClaude checks
.autoclaude/scripts/build-check.sh
.autoclaude/scripts/test-check.sh
.autoclaude/scripts/format-check.sh
.autoclaude/scripts/production-readiness.sh
.autoclaude/scripts/github-actions.sh
```

### Dependency Management
- Python dependencies via `uv` (Astra) - planned migration from pip
- Node.js dependencies for TypeScript/ESLint tooling
- Use `GITHUB_TOKEN` env var for authenticated GitHub API access

### Environment Setup
- Python 3.10+ required (check `.python-version`)
- VS Code workspace configured for Python environment management
- Pre-commit hooks configured (currently empty, to be populated)
- AutoClaude scripts require bash and common Unix tools

## Code Conventions

### Project Structure
- Keep harvesting tools in `tools/` directory
- System utilities in `cleanup/` and `dotfiles/`
- MCP server logic in `mcp_ingest/` with clear module separation
- Use `imports/` for permissively-licensed mirrored repositories

### Quality Standards
- Remove all TODO/FIXME comments before production deployment
- No debug console statements or debugger breakpoints
- Comprehensive test coverage required
- ESLint for TypeScript code formatting

### File Organization
- Python scripts use `.py` extension with executable permissions
- Shell scripts use `.sh` extension with proper shebang
- Configuration files follow standard naming (`.env.example`, `pyproject.toml`)

### Script Patterns
**Python Tools**: Follow the pattern in `tools/git_repo_backup.py`:
- Use `argparse` for CLI arguments with `--dry-run` defaults
- Include comprehensive docstrings and usage examples
- Use `logging` with structured format and timestamps
- Handle `GITHUB_TOKEN` environment variable for authentication

**Shell Scripts**: Follow the pattern in `cleanup/cleanup_desktop_and_kernels.sh`:
- Use `set -euo pipefail` for strict error handling
- Include `--dry-run` mode for safe execution
- Use functions for reusable logic
- Provide clear progress output

## Integration Patterns

### External Services
- **Codacy**: Code quality analysis - run after every edit
- **GitHub API**: Repository harvesting with token authentication
- **Cloudflare**: Secrets management for secure credential storage
- **Planned**: Confluence/Jira/Linear integrations, Neo4j knowledge graph

### Authentication Patterns
- Use `GITHUB_TOKEN` environment variable for GitHub API access
- Temporarily rewrite git remote URLs for authenticated pushes
- Store secrets in Cloudflare for secure access
- Use environment variables for all sensitive configuration

### Deployment
- Docker Compose for containerized deployment
- Multi-environment support (dev/prod) planned
- Automated backup via `tools/backup_rsync.sh`

### Data Flow
- GitHub repository ingestion → MCP processing → embeddings generation → database storage
- Backup workflows: filesystem scanning → Git push automation → external storage

## Common Patterns

### Error Handling
```python
# Use structured error handling with logging (from tools/git_repo_backup.py)
try:
    # operation
except Exception as e:
    logging.error(f"Operation failed: {e}")
    raise
```

### Command-line Argument Parsing
```python
# Use argparse for script parameters (from tools/git_repo_backup.py)
import argparse
p = argparse.ArgumentParser()
p.add_argument('--roots', nargs='+', default=['/home'], help='Root paths to scan')
p.add_argument('--dry-run', action='store_true', default=True, help='Only report (default)')
args = p.parse_args()
```

### Shell Script Structure
```bash
#!/usr/bin/env bash
# Use proper shebang and error handling (from cleanup/cleanup_desktop_and_kernels.sh)
set -euo pipefail

# Function definitions first
check_installed() {
    # implementation
}

# Main logic
echo "Starting cleanup..."
check_installed
```

### GitHub API Integration
```python
# Use token authentication for GitHub API (from tools/git_repo_backup.py)
token = os.environ.get('GITHUB_TOKEN')
if token:
    # Temporarily rewrite remote URL for authentication
    secure = origin.replace('https://github.com/', f'https://{token}@github.com/')
    run(f'git remote set-url origin {secure}', cwd=repo, check=True)
```

### Backup and Recovery Patterns
```bash
# Use rsync for efficient backups (from tools/backup_rsync.sh)
rsync -aAX --delete --exclude='node_modules' --exclude='.cache' "$SRC/" "$DEST/"
```

## Key Files Reference
- `tasks.md` - High-level project roadmap and immediate actions
- `.autoclaude/config.json` - Automated quality check configuration
- `tools/git_repo_backup.py` - Git repository backup automation with parallel processing
- `cleanup/cleanup_desktop_and_kernels.sh` - System maintenance with dry-run support
- `tools/backup_rsync.sh` - Rotated backup system with timestamp naming</content>
<parameter name="filePath">/home/cbwinslow/Documents/mcp-server/.github/copilot-instructions.md