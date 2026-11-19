#!/usr/bin/env bash
# Clean up after a merged or closed PR: delete its remote and local branch, return to the default branch.
# Usage: close-pr.sh <pr_number>
# Exit codes: 0 done, 1 stopped (see message), 2 usage error.
set -euo pipefail

pr="${1:-}"
pr="${pr#\#}"
[[ "$pr" =~ ^[0-9]+$ ]] || { echo "usage: close-pr.sh <pr_number>" >&2; exit 2; }

if [[ "$(git rev-parse --absolute-git-dir)" != "$(git rev-parse --path-format=absolute --git-common-dir)" ]]; then
  echo "stop: this is a linked worktree; run from the main checkout instead" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "stop: working tree has uncommitted or untracked changes; commit or stash them first" >&2
  exit 1
fi

info=$(gh pr view "$pr" --json state,headRefName,isCrossRepository,headRefOid \
  --jq '[.state, .headRefName, .isCrossRepository, .headRefOid] | @tsv') \
  || { echo "stop: PR #$pr not found" >&2; exit 1; }
IFS=$'\t' read -r state branch cross head <<<"$info"
echo "pr: #$pr $state ($branch)"

if [[ "$state" == "OPEN" ]]; then
  echo "stop: PR #$pr is still open; merge it on GitHub first" >&2
  exit 1
fi

default=$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)
local_tip=$(git rev-parse --verify --quiet "refs/heads/$branch" || true)

git cat-file -e "$head^{commit}" 2>/dev/null || git fetch --quiet origin "refs/pull/$pr/head" || true
if [[ "$branch" != "$default" && -n "$local_tip" ]] && ! git merge-base --is-ancestor "$local_tip" "$head" 2>/dev/null; then
  echo "stop: local $branch has commits that are not in PR #$pr; push or move them first" >&2
  exit 1
fi

wt_info=$(git worktree list --porcelain | awk -v b="branch refs/heads/$branch" '
  BEGIN { RS = ""; FS = "\n" }
  NR > 1 { hit = 0; lock = ""
    for (i = 1; i <= NF; i++) { if ($i == b) hit = 1; if ($i ~ /^locked/) lock = $i }
    if (hit) { print substr($1, 10); print lock; exit } }')
if [[ -n "$wt_info" ]]; then
  { read -r wt; read -r lock || true; } <<<"$wt_info"
  if [[ -n "$lock" ]]; then
    pid_re='\(pid ([0-9]+)'
    if ! [[ "$lock" =~ $pid_re ]] || kill -0 "${BASH_REMATCH[1]}" 2>/dev/null; then
      echo "stop: worktree $wt is $lock; exit that session or unlock it first" >&2
      exit 1
    fi
    git worktree unlock "$wt"
  fi
  git worktree remove "$wt" \
    || { echo "stop: worktree $wt has local changes; commit or remove them first" >&2; exit 1; }
  echo "worktree: removed $wt"
fi

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
  echo "local branch: deleted (was $(git rev-parse --short "$local_tip"))"
else
  echo "local branch: not found"
fi
