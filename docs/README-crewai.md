# CrewAI Agents for MCP Server

This directory contains CrewAI agent configurations and tools for intelligent automation of MCP server operations and GitHub repository harvesting workflows.

## Overview

The CrewAI integration provides AI-powered agents that can:

- **Monitor MCP Server Health**: Automatically check component status and performance
- **Manage Repository Harvesting**: Intelligently discover and process GitHub repositories
- **Perform Code Quality Analysis**: Run automated code reviews and security scans
- **Generate Embeddings**: Process harvested content for semantic search
- **Handle Database Operations**: Query and manage MCP server data

## Quick Start

### 1. Install Dependencies

```bash
# Install CrewAI and dependencies
pip install -r requirements-crewai.txt

# Or install from pyproject.toml
pip install -e .
```

### 2. Configure Environment

Set required environment variables:

```bash
export MCP_API_KEY="your-mcp-api-key"
export GITHUB_TOKEN="your-github-token"
export CODACY_API_TOKEN="your-codacy-token"
export OPENAI_API_KEY="your-openai-key"  # If using GPT models
```

### 3. Run Agents

```bash
# Run all agents as a crew
python crewai_agent.py

# Run specific task
python crewai_agent.py --task server_health_check

# Check agent status
python crewai_agent.py --status

# Initialize without running
python crewai_agent.py --init-only
```

## Configuration

### Main Configuration (`crewai_config.yaml`)

The main configuration file defines:

- **Agents**: Specialized AI agents with roles, goals, and tools
- **Tasks**: Specific operations agents can perform
- **Tools**: Custom tools for MCP server integration
- **Memory**: Agent memory and context management
- **Success Requirements**: Metrics and thresholds for success validation

### Agent Types

#### MCP Server Manager
- **Role**: MCP Server Operations Specialist
- **Responsibilities**:
  - Server health monitoring
  - Component status checks
  - Performance optimization
  - Database operations

#### Code Quality Analyst
- **Role**: Code Quality and Security Specialist
- **Responsibilities**:
  - Automated code analysis
  - Security vulnerability scanning
  - Quality metric tracking
  - Review automation

#### Repository Harvester
- **Role**: GitHub Repository Specialist
- **Responsibilities**:
  - Repository discovery
  - Content extraction
  - Metadata processing
  - Harvest pipeline management

### Custom Tools

#### MCP Server Tools

#### `mcp_server_status`
Check MCP server component health:

```python
tool = get_tool("mcp_server_status")
result = tool.run(component="all")
```

#### `mcp_database_query`
Execute database queries:

```python
tool = get_tool("mcp_database_query")
result = tool.run(query_type="select", table="repositories", limit=10)
```

#### `mcp_github_crawler`
Control repository crawling:

```python
tool = get_tool("mcp_github_crawler")
result = tool.run(action="start", target="python-repos")
```

#### `mcp_embeddings_generator`
Generate content embeddings:

```python
tool = get_tool("mcp_embeddings_generator")
result = tool.run(content_type="code", batch_size=50)
```

### External Service Tools

#### `codacy_analyze`
Run code quality analysis:

```python
tool = get_tool("codacy_analyze")
result = tool.run(target="project")
```

#### `github_repo_search`
Search GitHub repositories:

```python
tool = get_tool("github_repo_search")
result = tool.run(query="machine learning", language="python", min_stars=100)
```

#### `github_repo_clone`
Clone repositories:

```python
tool = get_tool("github_repo_clone")
result = tool.run(repo_url="https://github.com/user/repo.git")
```

#### `content_extractor`
Extract repository content:

```python
tool = get_tool("content_extractor")
result = tool.run(repo_path="/path/to/repo", content_types=["code", "docs"])
```

## Task Examples

### Server Health Check
```bash
python crewai_agent.py --task server_health_check
```

**Expected Output:**
```json
{
  "status": "success",
  "task_name": "server_health_check",
  "result": "All MCP server components are healthy. Database: OK, Crawler: OK, Extractor: OK, Embeddings: OK"
}
```

### Quality Analysis
```bash
python crewai_agent.py --task quality_analysis
```

**Expected Output:**
```json
{
  "status": "success",
  "task_name": "quality_analysis",
  "result": "Code quality analysis completed. Found 3 issues: 1 security vulnerability, 2 code smells. Recommendations provided."
}
```

### Repository Harvest
```bash
python crewai_agent.py --task repository_harvest
```

**Expected Output:**
```json
{
  "status": "success",
  "task_name": "repository_harvest",
  "result": "Successfully harvested 25 repositories. Processed 1500 files, generated 3000 embeddings."
}
```

## Success Monitoring

The system includes success requirements monitoring:

- **Server Uptime**: 99.9% uptime requirement
- **Quality Score**: Codacy grade A or higher
- **Harvest Rate**: 100 repositories per day minimum
- **Processing Time**: Under 5 minutes average per repository

Monitor success metrics:
```python
from crewai_agent import SuccessMonitor

monitor = SuccessMonitor(config)
results = monitor.check_requirements()
print(json.dumps(results, indent=2))
```

## Logging and Monitoring

All agent activities are logged to `logs/crewai_agent.log`. Execution results are automatically saved as JSON files in the `logs/` directory.

### Log Format
```
2024-01-15 10:30:15 - crewai_agent - INFO - Created agent: MCP Server Manager
2024-01-15 10:30:16 - crewai_agent - INFO - Crew execution completed successfully in 45.23 seconds
```

## Development

### Adding New Tools

1. Create tool class in `crewai_tools.py`
2. Add to `TOOL_REGISTRY`
3. Update `crewai_config.yaml` agents section
4. Test with individual tool functions

### Adding New Agents

1. Define agent configuration in `crewai_config.yaml`
2. Specify role, goal, backstory, and tools
3. Create corresponding tasks
4. Test agent initialization and execution

### Extending Tasks

1. Add task configuration to `crewai_config.yaml`
2. Define description, agent assignment, and expected output
3. Implement any required custom logic
4. Validate task execution

## Troubleshooting

### Common Issues

#### Import Errors
```
Error: No module named 'crewai'
```
**Solution**: Install dependencies
```bash
pip install -r requirements-crewai.txt
```

#### API Key Missing
```
Warning: Missing required environment variables: ['MCP_API_KEY']
```
**Solution**: Set environment variables
```bash
export MCP_API_KEY="your-key-here"
```

#### Server Connection Failed
```
Error: MCP server request failed: Connection refused
```
**Solution**: Ensure MCP server is running
```bash
# Start MCP server first
python -m mcp_ingest.main
```

### Debug Mode

Enable verbose logging:
```bash
export LOG_LEVEL=DEBUG
python crewai_agent.py
```

## Integration Examples

### With MCP Server
```python
from crewai_tools import get_tool

# Check server status
status_tool = get_tool("mcp_server_status")
status = status_tool.run()

# Query database
db_tool = get_tool("mcp_database_query")
repos = db_tool.run(table="repositories", limit=5)
```

### With GitHub API
```python
from crewai_tools import get_tool

# Search repositories
search_tool = get_tool("github_repo_search")
results = search_tool.run(query="python", min_stars=50)

# Clone repository
clone_tool = get_tool("github_repo_clone")
clone_tool.run(repo_url=results['repositories'][0]['clone_url'])
```

## Performance Optimization

### Memory Management
- Agents use conversation buffer memory by default
- Configure memory limits in `crewai_config.yaml`
- Monitor memory usage for long-running tasks

### Parallel Execution
- Tasks can be configured for async execution
- Use `async_execution: true` for parallel processing
- Monitor resource usage during parallel operations

### Caching
- Tool results are cached where appropriate
- Database query results cached for repeated calls
- GitHub API responses cached to respect rate limits

## Security Considerations

- API keys stored as environment variables
- No sensitive data logged in plain text
- HTTPS used for all external API calls
- Input validation on all tool parameters
- Rate limiting respected for external APIs

## Contributing

1. Follow existing code patterns in `crewai_tools.py`
2. Add comprehensive docstrings
3. Include error handling and logging
4. Test tools individually before integration
5. Update configuration examples
6. Document new features in this README