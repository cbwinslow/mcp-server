# CrewAI MCP Server Environment Setup

## Required Environment Variables

# MCP Server Configuration
export MCP_API_KEY="your-mcp-server-api-key"
export MCP_SERVER_URL="http://localhost:3000"

# GitHub Integration
export GITHUB_TOKEN="your-github-personal-access-token"

# Code Quality (Optional)
export CODACY_API_TOKEN="your-codacy-api-token"
export CODACY_ORG="your-codacy-organization"

# AI/LLM Configuration
export OPENAI_API_KEY="your-openai-api-key"

# Notification Webhooks (Optional)
export SLACK_WEBHOOK_URL="your-slack-webhook-url"

# Email Configuration (Optional)
export EMAIL_USERNAME="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"

## Installation

# Install Python dependencies
pip install -r requirements-crewai.txt

# Or install from pyproject.toml
pip install -e .

## Verification

# Check installation
python -c "import crewai; print('CrewAI installed successfully')"

# Test basic functionality
python crewai_agent.py --status

# Run demo
python demo_crewai_integration.py
