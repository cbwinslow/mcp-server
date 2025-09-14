#!/usr/bin/env python3
"""
CrewAI Agent Implementation for MCP Server
Main script to run AI agents that interact with MCP server components
"""

import os
import yaml
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Import CrewAI components (assuming crewai package is installed)
try:
    from crewai import Agent, Task, Crew, Process
    from crewai_tools import get_tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("Warning: CrewAI package not installed. Install with: pip install crewai")

# Import custom tools
from custom_crewai_tools import TOOL_REGISTRY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/crewai_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CrewAIAgentManager:
    """Manager class for CrewAI agents with MCP server integration"""

    def __init__(self, config_path: str = "crewai_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.agents = {}
        self.tasks = {}
        self.crew = None

        # Ensure log directory exists
        Path("logs").mkdir(exist_ok=True)

        # Validate environment
        self._validate_environment()

    def _load_config(self) -> Dict[str, Any]:
        """Load CrewAI configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration: {e}")
            raise

    def _validate_environment(self) -> None:
        """Validate required environment variables and dependencies"""
        required_vars = self.config.get('environment', {}).get('required_vars', [])
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.warning(f"Missing required environment variables: {missing_vars}")
            logger.warning("Some functionality may not work correctly")

        if not CREWAI_AVAILABLE:
            logger.error("CrewAI package is not installed")
            raise ImportError("CrewAI is required for agent functionality")

    def create_agents(self) -> None:
        """Create CrewAI agents from configuration"""
        agent_configs = self.config.get('agents', [])

        for agent_config in agent_configs:
            agent = self._create_agent(agent_config)
            self.agents[agent_config['name']] = agent
            logger.info(f"Created agent: {agent_config['name']}")

    def _create_agent(self, config: Dict[str, Any]) -> 'Agent':
        """Create a single CrewAI agent"""
        # Get tools for this agent
        tools = []
        for tool_name in config.get('tools', []):
            try:
                tool = get_tool(tool_name)
                tools.append(tool)
            except ValueError as e:
                logger.warning(f"Could not load tool '{tool_name}': {e}")

        # Create agent
        agent = Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            llm=config.get('llm', 'gpt-4'),
            memory=config.get('memory', True),
            max_iterations=config.get('max_iterations', 10),
            allow_delegation=config.get('allow_delegation', True),
            tools=tools,
            verbose=config.get('verbose', True)
        )

        return agent

    def create_tasks(self) -> None:
        """Create CrewAI tasks from configuration"""
        task_configs = self.config.get('tasks', [])

        for task_config in task_configs:
            task = self._create_task(task_config)
            self.tasks[task_config['name']] = task
            logger.info(f"Created task: {task_config['name']}")

    def _create_task(self, config: Dict[str, Any]) -> 'Task':
        """Create a single CrewAI task"""
        agent = self.agents.get(config['agent'])
        if not agent:
            raise ValueError(f"Agent '{config['agent']}' not found for task '{config['name']}'")

        task = Task(
            description=config['description'],
            agent=agent,
            expected_output=config['expected_output'],
            context=config.get('context', []),
            async_execution=config.get('async_execution', False)
        )

        return task

    def create_crew(self) -> None:
        """Create the main CrewAI crew"""
        crew_config = self.config.get('crewai_config', {})

        self.crew = Crew(
            agents=list(self.agents.values()),
            tasks=list(self.tasks.values()),
            process=crew_config.get('process', 'hierarchical'),
            memory=crew_config.get('memory', True),
            verbose=crew_config.get('verbose', True)
        )

        logger.info("Created CrewAI crew")

    def run_crew(self) -> Dict[str, Any]:
        """Execute the crew and return results"""
        if not self.crew:
            raise ValueError("Crew not initialized. Call create_crew() first.")

        logger.info("Starting crew execution")
        start_time = datetime.now()

        try:
            result = self.crew.kickoff()
            end_time = datetime.now()

            execution_result = {
                "status": "success",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - start_time).total_seconds(),
                "result": str(result)
            }

            logger.info(f"Crew execution completed successfully in {execution_result['duration_seconds']:.2f} seconds")
            return execution_result

        except Exception as e:
            end_time = datetime.now()
            error_result = {
                "status": "failed",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - start_time).total_seconds(),
                "error": str(e)
            }

            logger.error(f"Crew execution failed: {e}")
            return error_result

    def run_specific_task(self, task_name: str) -> Dict[str, Any]:
        """Run a specific task by name"""
        if task_name not in self.tasks:
            raise ValueError(f"Task '{task_name}' not found")

        task = self.tasks[task_name]
        agent = task.agent

        logger.info(f"Running specific task: {task_name}")

        try:
            result = agent.execute_task(task)
            return {
                "status": "success",
                "task_name": task_name,
                "result": str(result)
            }
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "status": "failed",
                "task_name": task_name,
                "error": str(e)
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of agents and tasks"""
        return {
            "agents": list(self.agents.keys()),
            "tasks": list(self.tasks.keys()),
            "crew_initialized": self.crew is not None,
            "config_loaded": bool(self.config)
        }

    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save execution results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crewai_results_{timestamp}.json"

        filepath = Path("logs") / filename
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Results saved to {filepath}")

class SuccessMonitor:
    """Monitor for success requirements and metrics"""

    def __init__(self, config: Dict[str, Any]):
        self.requirements = config.get('success_requirements', [])
        self.metrics = {}

    def check_requirements(self) -> Dict[str, Any]:
        """Check if success requirements are met"""
        results = {}

        for req in self.requirements:
            name = req['name']
            metric = req['metric']
            threshold = req['threshold']
            unit = req.get('unit', '')

            current_value = self.metrics.get(metric)

            if current_value is None:
                results[name] = {
                    "status": "unknown",
                    "message": f"Metric '{metric}' not available"
                }
                continue

            # Simple threshold checking (can be extended for different types)
            if isinstance(threshold, (int, float)):
                met = current_value >= threshold if unit in ['percent', 'count'] else current_value <= threshold
            else:
                met = str(current_value) == str(threshold)

            results[name] = {
                "status": "met" if met else "not_met",
                "current_value": current_value,
                "threshold": threshold,
                "unit": unit
            }

        return results

    def update_metric(self, metric: str, value: Any) -> None:
        """Update a metric value"""
        self.metrics[metric] = value

def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description="CrewAI Agent Manager for MCP Server")
    parser.add_argument('--config', default='crewai_config.yaml', help='Configuration file path')
    parser.add_argument('--task', help='Run specific task by name')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--init-only', action='store_true', help='Initialize agents and tasks without running')

    args = parser.parse_args()

    try:
        # Initialize agent manager
        manager = CrewAIAgentManager(args.config)

        # Create agents and tasks
        manager.create_agents()
        manager.create_tasks()

        if args.status:
            # Show status
            status = manager.get_status()
            print(json.dumps(status, indent=2))
            return

        if args.init_only:
            # Just initialize, don't run
            print("Agents and tasks initialized successfully")
            return

        if args.task:
            # Run specific task
            result = manager.run_specific_task(args.task)
            print(json.dumps(result, indent=2))

            # Save results
            manager.save_results(result)
        else:
            # Create and run full crew
            manager.create_crew()
            result = manager.run_crew()
            print(json.dumps(result, indent=2))

            # Save results
            manager.save_results(result)

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        exit(1)

if __name__ == "__main__":
    main()