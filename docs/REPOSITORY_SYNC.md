# Repository Sync to GitHub/GitLab/Bitbucket

This project includes a helper script to push the current repo to multiple remotes.

## Prereqs
- Ensure you have credentials set up (SSH keys or HTTPS tokens) for each remote.
- Create empty repositories on each platform.

## Usage

```
# Example: set remotes and branch (choose one org)
# GitHub (cbwinslow)
export REMOTE_GITHUB=git@github.com:cbwinslow/mcp-server.git
# or GitHub (Cloud-Curio)
# export REMOTE_GITHUB=git@github.com:Cloud-Curio/mcp-server.git

# GitLab (cbwinslow)
export REMOTE_GITLAB=git@gitlab.com:cbwinslow/mcp-server.git
# or GitLab (Cloud-Curio)
# export REMOTE_GITLAB=git@gitlab.com:Cloud-Curio/mcp-server.git

# Bitbucket (cbwinslow)
export REMOTE_BITBUCKET=git@bitbucket.org:cbwinslow/mcp-server.git
# or Bitbucket (Cloud-Curio)
# export REMOTE_BITBUCKET=git@bitbucket.org:Cloud-Curio/mcp-server.git
export BRANCH=main

# Push
bash scripts/tools/push_to_remotes.sh
```

The script will:
- Add `origin` (GitHub), `gitlab`, and `bitbucket` remotes if provided
- Push the current branch to each

You can re-run the script after commits. Adjust `BRANCH` as needed.
