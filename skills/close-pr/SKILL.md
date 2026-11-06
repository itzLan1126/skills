---
name: close-pr
description: Clean up after a merged or closed GitHub PR by deleting its remote and local branch and returning to the default branch. Use only when the user explicitly invokes /close-pr or asks to clean up a specific PR. Never closes or merges an open PR.
---

# Close PR

Run the bundled script. It performs every step and safety check; do not run the steps yourself.

## Resolve the PR number

- `/close-pr #<n>` or `/close-pr <n>`: use `<n>`.
- Bare `/close-pr`: use the PR created earlier in this conversation (for example, the URL or number printed by `gh pr create`). Never infer the PR from the current branch.
  - No PR in this conversation: stop and ask the user for the number.
  - More than one PR: list them and ask which one.

## Run

From the repository root:

```bash
bash <skill-dir>/scripts/close-pr.sh <n>
```

`<skill-dir>` is the directory containing this file.

The script, in order:

1. Stops if `git status --porcelain` shows any change, including untracked files. Nothing else runs.
2. Stops if the PR is `OPEN`; the user must merge it manually. `MERGED` and `CLOSED` continue.
3. Deletes the remote branch on `origin` unless the PR comes from a fork, the branch is the default or protected branch, or it is already gone.
4. Switches to the repository's default branch and runs `git pull --ff-only --prune`.
5. Force-deletes the local branch (`git branch -D`) if it exists.

## Report

Relay the script's output lines to the user. Exit code `1` means a stop condition; report the `stop:` reason and do nothing else. Do not retry, stash, merge, close the PR, or finish the remaining steps by hand. Exit code `2` means the number was invalid.

A deleted branch of a merged or closed PR can be restored from the PR page on GitHub ("Restore branch").
