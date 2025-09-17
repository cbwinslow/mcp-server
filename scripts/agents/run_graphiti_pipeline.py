#!/usr/bin/env python3
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / 'src'))

from crewai.crewai_agent import CrewAIAgentManager


def main():
    cfg = str(Path(__file__).resolve().parents[2] / 'config' / 'crewai_graphiti.yaml')
    manager = CrewAIAgentManager(cfg)
    manager.create_agents()
    manager.create_tasks()
    manager.create_crew()
    result = manager.run_crew()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

