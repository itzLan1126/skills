---
name: git
description: Inspect Git changes, organize logical commits, and write Conventional Commits messages. Use for /git, explicit commit requests, message drafting, type or scope selection, and commit planning or review. Execute commits only when requested; keep drafting and review read-only. Excludes general Git troubleshooting, branch strategy, and history repair.
---

# Git Commit Workflow

Create accurate, reviewable commits. Keep each commit focused on one logical change and describe only the content it records.

## Execution and Scope

- Treat `/git` or a clear request to commit as authorization to create local commits. Reuse existing authorization; do not request routine confirmation.
- Keep message drafting, type selection, diff review, and commit planning read-only. Do not stage or commit unless execution is requested. If the user requires approval, prepare the complete message or plan before waiting.
- Honor the requested repository, files, changes, and staged-only limits. A bare `/git` or an unrestricted commit request covers the current repository's staged, unstaged, and untracked changes. Identify the intended project changes before including files whose purpose is unclear.
- Continue only within that scope. Ask a focused question only when a concrete scope or authorization conflict prevents the next action; show the proposed resolution first.
- Follow explicit user constraints and applicable repository instructions. Check relevant contribution rules and commit-message configuration; use this skill's message defaults only where the repository leaves a choice.

## Inspect and Organize

Use the actual diff as the primary evidence. Inspect the index and working tree separately, and read relevant untracked files directly. Use recent history only when needed to establish local conventions.

```bash
git status --short --untracked-files=all
git diff --staged
git diff
```

For a message request based only on a supplied summary, use those facts without inventing implementation details or motivation.

Group changes by purpose:

- Keep a behavior change with the tests, documentation, and supporting changes it requires.
- Split unrelated changes, including changes within the same file. Keep related changes together across files.
- Order commits so each remains coherent where practical. Do not split a change merely because it touches different file types or supports more than one commit type.
- Account for every in-scope change in the plan, including anything intentionally left uncommitted.

## Stage the Next Commit

Inspect the entire existing index before adding anything. Adding specific files does not exclude content that was already staged.

| Existing index | Action |
| --- | --- |
| Empty | Stage only the files or hunks for the next planned commit. |
| One complete, in-scope logical change | Preserve that selection and commit it first. Do not add unstaged content to it. |
| Mixed purposes, incomplete change, or content outside the requested scope | Do not commit it as-is. Prepare a minimal plan to isolate the intended change while preserving all work. Reorganize the existing selection only if already authorized; otherwise request approval for that specific adjustment. |

A general commit request does not by itself authorize replacing the user's existing staged selection. Explicit permission to split or reorganize staged changes does. When authorized, preserve working-tree content and retain any out-of-scope staged content for later; never include it in the current commit.

Choose file or hunk staging as needed:

```bash
git add -- <specific-files>
git add -p -- <path>
```

Use `git add -p` when interactive input is supported; otherwise use a reviewed, checked patch applied to the index. Use broad staging only after verifying that everything it includes belongs to the same intended commit.

Re-read the complete staged diff after staging. Proceed only when it contains exactly the intended logical change within the authorized scope.

## Commit Message Defaults

Use [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<scope>): <subject>

<body>

<footer>
```

Omit the scope and its parentheses when they add no useful context. Omit the body and footer when unnecessary. Apply repository-specific formatting rules when present.

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

- Use clear, controlled English inspired by ASD-STE100, unless the user or repository specifies another language. Do not claim formal compliance.
- Start the subject with a lowercase imperative verb when natural. State the main behavior or purpose, use consistent terms, and omit the final period.
- Aim for fewer than 50 characters in the subject when clarity permits. Obey any configured length limit for the complete header.
- Avoid vague subjects such as `update`, `fix bug`, or `misc` and unsupported claims about results or motivation.
- Add a body only for useful context: verified motivation, behavior, constraints, design decisions, or impact. Do not repeat the subject or force a fixed paragraph count.

```text
fix(auth): reject expired tokens
feat(settings): add proxy selector
docs: clarify deployment instructions
```

### Breaking Changes and Reverts

For an incompatible change that requires consumers to adapt, put `!` immediately before the header's colon, add a `BREAKING CHANGE:` footer, or use both. Describe what breaks in the subject or footer; include migration guidance when known.

```text
feat(api)!: remove legacy auth endpoint

BREAKING CHANGE: Use /v2/auth instead of /v1/auth.
```

Use issue references, migration instructions, and reverted commit hashes only when verified. For a revert, identify the original commit and explain the reason when available.

## Verify and Commit

1. Confirm that the staged content and message match the planned change. Run repository-required checks; reuse applicable results and add checks only for a concrete remaining risk.
2. Create the commit with safely quoted arguments. For a multiline message, prefer a message file passed to `git commit -F` so its exact text and line breaks are preserved.
3. Check whether the command succeeded. Verify the created commit's content, actual hash, and message before reporting success or advancing to the next group.
4. Recheck repository state and process the next in-scope group until the requested work is complete.

If a commit or required check fails, stop the commit sequence and inspect the cause and current state. Fix only issues within existing authorization, then recheck the staged diff before retrying. If a hook or another process changes files or the index, reassess the affected content before continuing. Report any unresolved blocker and the concrete work remaining.

Do not bypass hooks or change signing or identity settings to force a commit. Do not push, amend, rewrite history, or discard changes unless the user explicitly requests the relevant action.

## Output

After execution, list verified successful commits in order:

```text
<short-hash> <actual commit subject>
```

State any remaining in-scope changes and why they were left uncommitted. Distinguish partial completion from success. Mention out-of-scope changes only when useful; do not claim the working tree is clean unless verified.

For drafting or review, return the requested message, analysis, or per-commit plan. Include file or hunk guidance when useful, and runnable commands only when requested. Do not claim that proposed commits were created.

## Git References

- [Staging semantics and patch selection](https://git-scm.com/docs/git-add)
- [Commit behavior, message options, and hooks](https://git-scm.com/docs/git-commit)
