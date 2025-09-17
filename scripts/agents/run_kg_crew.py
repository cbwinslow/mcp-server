#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / 'src'))

from crewai.crewai_agent import CrewAIAgentManager


def main():
    cfg = str(Path(__file__).resolve().parents[2] / 'config' / 'crewai_kg.yaml')
    manager = CrewAIAgentManager(cfg)
    manager.create_agents()
    manager.create_tasks()
    manager.create_crew()
    result = manager.run_crew()
    print(result)


if __name__ == '__main__':
    main()

