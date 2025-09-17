#!/usr/bin/env python3
import asyncio
import json
from src.agents.validator import run_validation


async def main():
    report = await run_validation()
    print(json.dumps(report))


if __name__ == '__main__':
    asyncio.run(main())

