#!/usr/bin/env python3
"""Deterministic commit helpers: lint a message, stage hunks, commit and verify."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys

TYPES = ('feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'build', 'ci', 'chore', 'revert')
HEADER = re.compile(r'(?P<type>[^(!:\s]+)(?:\((?P<scope>[^()\s][^()]*)\))?(?P<bang>!)?: (?P<subject>.*)')
BREAKING = re.compile(r'BREAKING[ -]CHANGE')


def git(*args, input=None, check=True):
    result = subprocess.run(['git', *args], input=input, capture_output=True, text=True)
    if check and result.returncode:
        sys.exit(f'error: git {args[0]} failed: {result.stderr.strip()}')
    return result


def lint_errors(text, max_header):
    lines = text.rstrip('\n').split('\n')
    header = lines[0]
    if not header.strip():
        return ['header is empty']
    errors = []
    match = HEADER.fullmatch(header)
    if not match:
        errors.append('header must match "type(scope)!: subject"')
    else:
        if match['type'] not in TYPES:
            errors.append(f'unknown type {match["type"]!r}; use one of: {", ".join(TYPES)}')
        subject = match['subject']
        if not subject.strip():
            errors.append('subject is empty')
        elif subject.rstrip().endswith('.'):
            errors.append('subject must not end with a period')
    if len(header) > max_header:
        errors.append(f'header is {len(header)} characters; limit is {max_header}')
    if len(lines) > 1 and lines[1].strip():
        errors.append('separate the header from the body with one blank line')
    for line in lines[1:]:
        if BREAKING.match(line) and not re.fullmatch(r'BREAKING[ -]CHANGE: \S.*', line):
            errors.append(f'breaking footer must be "BREAKING CHANGE: <description>": {line!r}')
    return errors


def read_message(path):
    return sys.stdin.read() if path == '-' else Path(path).read_text(encoding='utf-8')


def report_lint(text, max_header):
    errors = lint_errors(text, max_header)
    for error in errors:
        print(f'lint: {error}', file=sys.stderr)
    return 1 if errors else 0


def cmd_lint(args):
    return report_lint(read_message(args.message), args.max_header)


def file_hunks(path):
    # Explicit prefixes keep the patch applicable whatever the user's diff config is.
    diff = git('diff', '--no-color', '--no-ext-diff', '--src-prefix=a/', '--dst-prefix=b/', '--', path).stdout
    if not diff:
        if git('ls-files', '--error-unmatch', '--', path, check=False).returncode:
            sys.exit(f'error: {path} is untracked; stage the whole file with git add')
        sys.exit(f'error: no unstaged changes in {path}')
    if diff.count('\ndiff --git ') or not diff.startswith('diff --git '):
        sys.exit(f'error: {path} must name exactly one file')
    parts = re.split(r'^(?=@@ )', diff, flags=re.MULTILINE)
    if len(parts) < 2:
        sys.exit(f'error: {path} has no text hunks; stage it with git add')
    return parts[0], parts[1:]


def hunk_id(hunk):
    # Hash the worktree start line and body. Staging other hunks changes neither, so the ID
    # stays valid; the start line keeps identical hunks distinct; editing the file invalidates it.
    header, _, body = hunk.partition('\n')
    start = re.match(r'@@ -\S+ \+(\d+)', header)[1]
    return hashlib.sha1(f'{start}\n{body}'.encode()).hexdigest()[:7]


def cmd_hunks(args):
    _, hunks = file_hunks(args.path)
    for hunk in hunks:
        print(f'[{hunk_id(hunk)}]')
        print(hunk, end='' if hunk.endswith('\n') else '\n')
    return 0


def cmd_stage(args):
    header, hunks = file_hunks(args.path)
    ids = [hunk_id(hunk) for hunk in hunks]
    picks = set(args.hunks.split(','))
    for pick in picks:
        if ids.count(pick) != 1:
            sys.exit(f'error: hunk {pick!r} is unknown or ambiguous; re-run hunks for current IDs')
    chosen = [hunk for hunk, id_ in zip(hunks, ids) if id_ in picks]
    # git apply is atomic: on any failure the index stays unchanged.
    git('apply', '--cached', input=header + ''.join(chosen))
    print(f'staged {len(chosen)} of {len(hunks)} hunks in {args.path}')
    return 0


def operation_in_progress():
    for ref in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD'):
        if git('rev-parse', '-q', '--verify', ref, check=False).returncode == 0:
            return ref
    if git('diff', '--name-only', '--diff-filter=U').stdout:
        return 'unmerged files'
    return None


def cmd_commit(args):
    operation = operation_in_progress()
    if operation:
        print(f'error: {operation} found; a merge, cherry-pick, revert, or conflict is in progress',
              file=sys.stderr)
        return 4
    text = read_message(args.message)
    if not args.skip_lint and report_lint(text, args.max_header):
        return 1
    if git('diff', '--cached', '--quiet', check=False).returncode == 0:
        sys.exit('error: nothing staged')
    tree = git('write-tree').stdout.strip()
    result = subprocess.run(['git', 'commit', '-q', '-F', '-'], input=text, text=True)
    if result.returncode:
        sys.exit('error: git commit failed; inspect the hook output and repository state')
    print(git('log', '-1', '--format=%h %s').stdout, end='')
    if git('rev-parse', 'HEAD^{tree}').stdout.strip() != tree:
        print('error: commit created, but its content differs from the staged content; a hook changed files',
              file=sys.stderr)
        return 3
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    lint = sub.add_parser('lint', help='check a message against Conventional Commits')
    lint.add_argument('message', nargs='?', default='-', help='message file; default: stdin')
    lint.add_argument('--max-header', type=int, default=72)
    lint.set_defaults(func=cmd_lint)
    hunks = sub.add_parser('hunks', help='list unstaged hunks of one tracked file with stable IDs')
    hunks.add_argument('path')
    hunks.set_defaults(func=cmd_hunks)
    stage = sub.add_parser('stage', help='stage hunks by ID, e.g. stage app.py 1a2b3c4,5d6e7f8')
    stage.add_argument('path')
    stage.add_argument('hunks')
    stage.set_defaults(func=cmd_stage)
    commit = sub.add_parser('commit', help='lint, commit the index, and verify the result')
    commit.add_argument('message', nargs='?', default='-', help='message file; default: stdin')
    commit.add_argument('--max-header', type=int, default=72)
    commit.add_argument('--skip-lint', action='store_true')
    commit.set_defaults(func=cmd_commit)
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
