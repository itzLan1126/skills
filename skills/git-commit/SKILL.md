---
name: git-commit
description: Inspect Git changes, organize logical commits, and write Conventional Commits messages. Use for /git-commit, explicit commit requests, message drafting, commit planning, and commit review. Excludes general Git troubleshooting, branch strategy, and history repair.
---

# Git Commit Workflow

## Execution and Scope

- Treat `/git-commit` or a clear request to commit as authorization to create local commits. Reuse existing authorization; do not request routine confirmation.
- Keep drafting, review, and planning read-only. Do not stage or commit unless execution is requested. If the user requires approval, prepare the complete message or plan before waiting.
- Honor the requested repository, files, changes, and staged-only limits. A bare `/git-commit` or an unrestricted commit request covers the current repository's staged, unstaged, and untracked changes. Identify the intended project changes before including files whose purpose is unclear.
- Check relevant contribution rules and commit-message configuration; use this skill's message defaults only where the repository leaves a choice.

## Inspect and Organize

Use the actual diff as the primary evidence. Inspect the index and working tree separately, and read relevant untracked files directly.

For a message request based only on a supplied summary, use those facts without inventing implementation details or motivation.

Group changes by purpose:

- Keep a behavior change with the tests, documentation, and supporting changes it requires.
- Split unrelated changes, including changes within the same file. Keep related changes together across files.
- Order commits so each remains coherent where practical. Do not split a change merely because it touches different file types or supports more than one commit type.
- Account for every in-scope change in the plan, including anything intentionally left uncommitted.

## Stage the Next Commit

Adding specific files does not exclude content that was already staged, so act on the existing index first:

| Existing index | Action |
| --- | --- |
| Empty | Stage only the files or hunks for the next planned commit. |
| One complete, in-scope logical change | Preserve that selection and commit it first. Do not add unstaged content to it. |
| Mixed purposes, incomplete change, or content outside the requested scope | Do not commit it as-is. Prepare a minimal plan to isolate the intended change while preserving all work. Reorganize the existing selection only with explicit permission to split or reorganize staged changes; a general commit request is not enough. When authorized, keep out-of-scope staged content for later and never include it in the current commit. |

Stage whole files with `git add -- <specific-files>`. To stage part of a tracked file, list its unstaged hunks, then stage the chosen hunk IDs:

```bash
python3 <skill-dir>/scripts/git_commit.py hunks <path>
python3 <skill-dir>/scripts/git_commit.py stage <path> <id>,<id>
```

`<skill-dir>` is the directory containing this file. Hunk IDs stay valid after other hunks are staged. When a single hunk mixes purposes, apply a reviewed patch with `git apply --cached`.

## Commit Message Defaults

Use [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). Omit the scope when it adds no useful context, and the body and footer when unnecessary.

### Type and Scope

Choose the type from the change's primary purpose, not its filenames.

| Type | Purpose |
| --- | --- |
| `feat` | New capability for users or consuming code |
| `fix` | Correction of broken behavior or a regression |
| `docs` | Documentation-only change |
| `style` | Formatting or code style without behavior changes |
| `refactor` | Internal restructuring without intended behavior changes |
| `perf` | Performance or resource-use improvement |
| `test` | Test changes without production behavior changes |
| `build` | Build system, packaging, or dependency change |
| `ci` | CI/CD configuration or automation |
| `chore` | Maintenance not covered by another type |
| `revert` | Reversal of a previous change |

Use an established repository scope when available; otherwise choose a specific module, feature, package, or subsystem. Omit vague scopes that add no information.

### Subject and Body

- Use clear, controlled English inspired by ASD-STE100, unless the user or repository specifies another language.
- Start the subject with a lowercase imperative verb when natural. State the main behavior or purpose and use consistent terms.
- Aim for fewer than 50 characters in the subject when clarity permits.
- Avoid vague subjects such as `update`, `fix bug`, or `misc` and unsupported claims about results or motivation.
- Add a body only for useful context: verified motivation, behavior, constraints, design decisions, or impact. Do not repeat the subject or force a fixed paragraph count.
- Mark an incompatible change with `!` before the colon and a `BREAKING CHANGE:` footer that says what breaks, with migration guidance when known.

```text
fix(auth): reject expired tokens
feat(api)!: remove legacy auth endpoint
docs: clarify deployment instructions
```

Use issue references, migration instructions, and reverted commit hashes only when verified. For a revert, identify the original commit and explain the reason when available.

## Verify and Commit

1. Confirm that the staged content and message match the planned change. Run repository-required checks; reuse applicable results and add checks only for a concrete remaining risk.
2. Commit with the message on standard input:

   ```bash
   python3 <skill-dir>/scripts/git_commit.py commit <<'EOF'
   feat(api): add token refresh
   EOF
   ```

   The script lints the message, commits the index, and verifies that the commit records exactly the staged content. Pass `--max-header N` for a configured header limit (default 72). When the repository defines its own message rules, follow them and pass `--skip-lint`.

   | Exit | Meaning |
   | --- | --- |
   | `0` | Commit created and verified; prints `<short-hash> <subject>`. |
   | `3` | Commit created and printed, but a hook changed its content. Count it as created; stop and report the difference. |
   | Other | No commit created: lint, staging, arguments, or `git commit` failed. |
3. Recheck repository state and process the next in-scope group until the requested work is complete.

If a commit or required check fails, stop the commit sequence and inspect the cause and current state. Fix only issues within existing authorization, then recheck the staged diff before retrying. If a hook changed files or the index, reassess the affected content before continuing.

Do not bypass hooks or change signing or identity settings to force a commit. Do not push, amend, rewrite history, or discard changes unless the user explicitly requests the relevant action.

## Output

After execution, list the `<short-hash> <subject>` line printed for each commit, in order. State any unresolved blocker and the remaining in-scope changes with why they were left uncommitted. Distinguish partial completion from success. Mention out-of-scope changes only when useful; do not claim the working tree is clean unless verified.

For drafting or review, return the requested message, analysis, or per-commit plan. Check a drafted message by piping it to `python3 <skill-dir>/scripts/git_commit.py lint` (same `--max-header` option) unless the repository defines its own message rules. Include file or hunk guidance when useful, and runnable commands only when requested. Do not claim that proposed commits were created.
