#!/usr/bin/env python3
"""
CrewAI MCP Server Integration Demo
Demonstrates complete integration of CrewAI agents with MCP server
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path

# Import our custom modules
from crewai_agent import CrewAIAgentManager, SuccessMonitor
from crewai_tools import TOOL_REGISTRY

async def demo_basic_integration():
    """Demonstrate basic CrewAI MCP integration"""
    print("🚀 Starting CrewAI MCP Server Integration Demo")
    print("=" * 50)

    # Initialize agent manager
    manager = CrewAIAgentManager("crewai_config.yaml")

    # Create agents and tasks
    print("📋 Creating agents and tasks...")
    manager.create_agents()
    manager.create_tasks()

    # Show status
    status = manager.get_status()
    print(f"✅ Initialized: {len(status['agents'])} agents, {len(status['tasks'])} tasks")

    # Run health check task
    print("\n🏥 Running server health check...")
    result = manager.run_specific_task("server_health_check")
    print(f"Result: {json.dumps(result, indent=2)}")

    return manager

async def demo_advanced_features():
    """Demonstrate advanced memory and success monitoring features"""
    print("\n🧠 Demonstrating Advanced Features")
    print("=" * 50)

    # Load advanced configuration
    with open("crewai_advanced_config.yaml", 'r') as f:
        advanced_config = json.load(f)  # Note: Using json for demo, normally use yaml

    # Initialize success monitor
    success_monitor = SuccessMonitor(advanced_config)

    # Simulate some metrics
    print("📊 Updating success metrics...")
    success_monitor.update_metric("uptime_percentage", 99.9)
    success_monitor.update_metric("quality_score", 97.5)
    success_monitor.update_metric("repos_harvested", 150)
    success_monitor.update_metric("avg_processing_time", 180)  # seconds

    # Check requirements
    print("🔍 Checking success requirements...")
    requirements_check = success_monitor.check_requirements()
    print(f"Requirements status: {json.dumps(requirements_check, indent=2)}")

    return success_monitor

async def demo_tool_integration():
    """Demonstrate individual tool usage"""
    print("\n🔧 Demonstrating Tool Integration")
    print("=" * 50)

    from custom_crewai_tools import get_tool

    # Test MCP server status tool
    print("Testing MCP server status tool...")
    try:
        status_tool = get_tool("mcp_server_status")
        result = status_tool.run("all")
        print(f"Server status: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Note: MCP server status check failed (expected if server not running): {e}")

    # Test GitHub search tool
    print("\nTesting GitHub repository search...")
    try:
        search_tool = get_tool("github_repo_search")
        result = search_tool.run(query="python", min_stars=10, limit=5)
        print(f"GitHub search results: Found {result.get('total_count', 0)} repositories")
        if result.get('repositories'):
            print(f"Sample repo: {result['repositories'][0]['full_name']}")
    except Exception as e:
        print(f"GitHub search failed: {e}")

    # Test content extractor
    print("\nTesting content extractor...")
    try:
        extractor_tool = get_tool("content_extractor")
        # Test with current directory
        result = extractor_tool.run(str(Path.cwd()))
        print(f"Content extraction: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Content extraction failed: {e}")

def create_environment_setup():
    """Create environment setup instructions"""
    setup_content = """# CrewAI MCP Server Environment Setup

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
"""

    with open("environment_setup.md", 'w') as f:
        f.write(setup_content)

    print("📝 Created environment setup documentation")

async def main():
    """Main demo function"""
    print("🤖 CrewAI MCP Server Integration Demo")
    print("This demo showcases the complete integration of CrewAI agents with MCP server")
    print()

    # Create environment setup
    create_environment_setup()

    # Run basic integration demo
    manager = await demo_basic_integration()

    # Run advanced features demo
    success_monitor = await demo_advanced_features()

    # Run tool integration demo
    await demo_tool_integration()

    print("\n🎉 Demo completed successfully!")
    print("\nNext steps:")
    print("1. Set up environment variables (see environment_setup.md)")
    print("2. Start MCP server: python -m mcp_ingest.main")
    print("3. Run agents: python crewai_agent.py")
    print("4. Monitor results: tail -f logs/crewai_agent.log")

if __name__ == "__main__":
    asyncio.run(main())