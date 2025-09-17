#!/usr/bin/env bash
set -euo pipefail

REMOTE_USER=${1:-cbwinslow}
ORG=${2:-Cloud-Curio}

echo "==> Ensure remotes exist"
git remote add github git@github.com:${ORG}/mcp-server.git 2>/dev/null || true
git remote add gitlab git@gitlab.com:${ORG}/mcp-server.git 2>/dev/null || true
git remote add bitbucket git@bitbucket.org:${ORG}/mcp-server.git 2>/dev/null || true

echo "==> Pushing to GitHub/GitLab/Bitbucket"
git push -u github HEAD:main || true
git push -u gitlab HEAD:main || true
git push -u bitbucket HEAD:main || true

