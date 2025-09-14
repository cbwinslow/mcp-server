#!/usr/bin/env python3
"""Scan filesystem for git repos and optionally push local commits to origin.

Usage:
  python3 tools/git_repo_backup.py --roots /home /srv --dry-run
  python3 tools/git_repo_backup.py --roots /home --push --parallel 4

Notes:
- Default is dry-run. Set --push to actually push. Use GITHUB_TOKEN env var if you want
  to authenticate HTTPS pushes for GitHub (script will temporarily rewrite remote URL).
"""
from __future__ import annotations
import argparse
import subprocess
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def find_git_repos(roots: list[Path]) -> list[Path]:
    repos = []
    for root in roots:
        for p in root.rglob('.git'):
            repo = p.parent
            repos.append(repo)
    # deduplicate and sort
    unique = sorted(set(repos))
    return unique


def run(cmd, cwd=None, capture=False, check=False):
    logging.debug("RUN %s @%s", cmd, cwd)
    res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=capture, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{res.stderr}")
    return res


def repo_status(repo: Path) -> dict:
    try:
        r = run('git rev-parse --abbrev-ref HEAD', cwd=repo, capture=True)
        branch = r.stdout.strip()
        res = run('git status --porcelain', cwd=repo, capture=True)
        dirty = bool(res.stdout.strip())
        # check for upstream
        up = run('git rev-parse --abbrev-ref --symbolic-full-name @{u}', cwd=repo, capture=True)
        has_upstream = up.returncode == 0
    except Exception as e:
        logging.warning('Failed to inspect %s: %s', repo, e)
        return {'repo': str(repo), 'error': str(e)}
    return {'repo': str(repo), 'branch': branch, 'dirty': dirty, 'has_upstream': has_upstream}


def push_repo(repo: Path, token: str | None) -> dict:
    info = {'repo': str(repo)}
    try:
        # ensure fetch
        run('git fetch --all --prune', cwd=repo, check=False)
        # find if local branch is ahead of origin
        r = run('git status --porcelain -b', cwd=repo, capture=True)
        status = r.stdout
        if 'ahead' not in status and 'behind' not in status and 'diverged' not in status and '##' in status:
            info['pushed'] = False
            info['reason'] = 'no unpushed commits detected'
            return info
        # get origin URL
        r = run('git remote get-url origin', cwd=repo, capture=True)
        origin = r.stdout.strip()
        use_token = token and origin.startswith('https://github.com/')
        if use_token:
            # rewrite to include token for push
            secure = origin.replace('https://github.com/', f'https://{token}@github.com/')
            run(f'git remote set-url origin {secure}', cwd=repo, check=True)
        # attempt push
        p = run('git push --all origin', cwd=repo, capture=True)
        info['returncode'] = p.returncode
        if p.returncode == 0:
            info['pushed'] = True
        else:
            info['pushed'] = False
            info['output'] = p.stderr + '\n' + p.stdout
        if use_token:
            # restore original URL
            run(f'git remote set-url origin {origin}', cwd=repo, check=False)
    except Exception as e:
        info['error'] = str(e)
    return info


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--roots', nargs='+', default=['/home'], help='Root paths to scan')
    p.add_argument('--dry-run', action='store_true', default=True, help='Only report (default)')
    p.add_argument('--push', action='store_true', help='Actually push changes')
    p.add_argument('--parallel', type=int, default=4)
    args = p.parse_args()

    roots = [Path(r).expanduser() for r in args.roots]
    logging.info('Scanning roots: %s', roots)
    repos = find_git_repos(roots)
    logging.info('Found %d repositories', len(repos))

    report = []
    token = os.environ.get('GITHUB_TOKEN')
    if args.dry_run and not args.push:
        logging.info('Dry-run mode (no pushes). Use --push to perform pushes.')

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futures = {ex.submit(repo_status, repo): repo for repo in repos}
        for f in as_completed(futures):
            info = f.result()
            report.append(info)

    # summarize
    for r in report:
        if 'error' in r:
            logging.warning('%s -> error: %s', r.get('repo'), r.get('error'))
        else:
            logging.info('%s [%s] dirty=%s upstream=%s', r.get('repo'), r.get('branch', '?'), r.get('dirty'), r.get('has_upstream'))

    if args.push:
        push_reports = []
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futures = {ex.submit(push_repo, Path(r['repo']), token): r for r in report if 'repo' in r}
            for f in as_completed(futures):
                res = f.result()
                push_reports.append(res)
                logging.info('Push result: %s -> %s', res.get('repo'), res.get('pushed'))
    logging.info('Done')


if __name__ == '__main__':
    main()
