#!/usr/bin/env bash
# Clean up after a merged or closed PR: delete its remote and local branch, return to the default branch.
# Usage: close-pr.sh <pr_number>
# Exit codes: 0 done, 1 stopped (see message), 2 usage error.
set -euo pipefail

pr="${1:-}"
pr="${pr#\#}"
[[ "$pr" =~ ^[0-9]+$ ]] || { echo "usage: close-pr.sh <pr_number>" >&2; exit 2; }

if [[ -n "$(git status --porcelain)" ]]; then
  echo "stop: working tree has uncommitted or untracked changes; commit or stash them first" >&2
  exit 1
fi

info=$(gh pr view "$pr" --json state,headRefName,isCrossRepository \
  --jq '[.state, .headRefName, .isCrossRepository] | @tsv') \
  || { echo "stop: PR #$pr not found" >&2; exit 1; }
IFS=$'\t' read -r state branch cross <<<"$info"
echo "pr: #$pr $state ($branch)"

if [[ "$state" == "OPEN" ]]; then
  echo "stop: PR #$pr is still open; merge it on GitHub first" >&2
  exit 1
fi

default=$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)

if [[ "$cross" == "true" ]]; then
  echo "remote branch: skipped (fork)"
elif [[ "$branch" == "$default" ]]; then
  echo "remote branch: skipped (default branch)"
elif ! git ls-remote --exit-code --heads origin "$branch" >/dev/null; then
  echo "remote branch: already deleted"
elif [[ "$(gh api "repos/{owner}/{repo}/branches/$branch" --jq .protected)" == "true" ]]; then
  echo "remote branch: skipped (protected)"
else
  git push --quiet origin --delete "$branch"
  echo "remote branch: deleted"
fi

git switch --quiet "$default"
git pull --quiet --ff-only --prune
echo "switched to: $default (pulled)"

if [[ "$branch" == "$default" ]]; then
  echo "local branch: skipped (default branch)"
elif git show-ref --verify --quiet "refs/heads/$branch"; then
  git branch --quiet -D "$branch"
  echo "local branch: deleted"
else
  echo "local branch: not found"
fi
