"""git_commit.py against a temp repo."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills' / 'git-commit' / 'scripts' / 'git_commit.py'
ENV = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
       'GIT_COMMITTER_EMAIL': 't@t', 'GIT_CONFIG_GLOBAL': os.devnull}
BASE = ''.join(f'line {n}\n' for n in range(1, 21))


class GitCommitTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.git('init', '-q', '-b', 'main')
        self.write('app.txt', BASE)
        self.git('add', 'app.txt')
        self.git('commit', '-q', '-m', 'init')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, env=ENV, capture_output=True, text=True,
                              check=True).stdout

    def write(self, name, text):
        (self.repo / name).write_text(text)

    def run_script(self, *args, input=None):
        return subprocess.run(['python3', str(SCRIPT), *args], cwd=self.repo, env=ENV,
                              capture_output=True, text=True, input=input)

    def lint(self, message, *extra):
        return self.run_script('lint', *extra, input=message)

    def hunk_ids(self):
        listed = self.run_script('hunks', 'app.txt')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        return [line[1:-1] for line in listed.stdout.splitlines() if line.startswith('[')]

    def test_lint_accepts_valid_messages(self):
        for message in ('fix(auth): reject expired tokens\n',
                        'docs: clarify setup',
                        'feat(api)!: remove legacy endpoint\n\nBody.\n\nBREAKING CHANGE: Use /v2/auth.\n',
                        'refactor: split parser\n\nBREAKING-CHANGE: parse() now returns a list\n',
                        'fix: add x\n\nBreaking changes are none.\n'):
            with self.subTest(message=message):
                result = self.lint(message)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_lint_rejects_invalid_messages(self):
        cases = [
            ('', 'header is empty'),
            ('update stuff\n', 'must match'),
            ('feature: add x\n', 'unknown type'),
            ('Fix: add x\n', 'unknown type'),
            ('fix():  add x\n', 'must match'),
            ('fix: \n', 'subject is empty'),
            ('fix: add x.\n', 'period'),
            (f'fix: {"a" * 70}\n', 'limit is 72'),
            ('fix: add x\nbody\n', 'blank line'),
            ('feat!: drop x\n\nBREAKING CHANGE gone\n', 'BREAKING CHANGE'),
            ('feat!: drop x\n\nBREAKING CHANGE:\n', 'BREAKING CHANGE'),
        ]
        for message, expected in cases:
            with self.subTest(message=message):
                result = self.lint(message)
                self.assertEqual(result.returncode, 1)
                self.assertIn(expected, result.stderr)

    def test_lint_max_header_override(self):
        self.assertEqual(self.lint('fix: add something\n', '--max-header', '10').returncode, 1)

    def test_lint_reads_file(self):
        self.write('msg', 'fix: add x.\n')
        self.assertEqual(self.run_script('lint', 'msg').returncode, 1)

    def test_stage_selected_hunks_only(self):
        lines = BASE.splitlines(keepends=True)
        lines[0] = 'first changed\n'
        lines[9] = 'middle changed\n'
        lines[19] = 'last changed\n'
        self.write('app.txt', ''.join(lines))
        first, middle, last = self.hunk_ids()
        result = self.run_script('stage', 'app.txt', f'{last},{first}')
        self.assertEqual(result.returncode, 0, result.stderr)
        staged = self.git('diff', '--cached')
        self.assertIn('+first changed', staged)
        self.assertIn('+last changed', staged)
        self.assertNotIn('middle changed', staged)
        self.assertEqual(self.hunk_ids(), [middle])
        result = self.run_script('stage', 'app.txt', middle)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('diff'), '')

    def test_identical_hunks_get_distinct_ids(self):
        block = 'x\ny\nz\n{}\nx\ny\nz\n'
        text = 'a\n' + block + BASE + block + 'b\n'
        self.write('app.txt', text.format('old', 'old'))
        self.git('commit', '-qam', 'blocks')
        self.write('app.txt', text.format('new', 'new'))
        first, second = self.hunk_ids()
        self.assertNotEqual(first, second)
        result = self.run_script('stage', 'app.txt', second)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('diff', '--cached').count('+new'), 1)
        self.assertEqual(self.hunk_ids(), [first])

    def test_edited_file_invalidates_ids(self):
        self.write('app.txt', 'top\n' + BASE + 'more\n')
        _, bottom = self.hunk_ids()
        self.write('app.txt', BASE + 'more\n')
        self.assertIn('re-run hunks', self.run_script('stage', 'app.txt', bottom).stderr)

    def test_stage_rejects_bad_input(self):
        self.assertEqual(self.run_script('hunks', 'app.txt').returncode, 1)
        self.write('new.txt', 'new\n')
        self.assertIn('untracked', self.run_script('hunks', 'new.txt').stderr)
        self.write('app.txt', BASE + 'more\n')
        (valid,) = self.hunk_ids()
        for picks in ('1', 'zzzzzzz', '', f'{valid},zzzzzzz'):
            with self.subTest(picks=picks):
                result = self.run_script('stage', 'app.txt', picks)
                self.assertEqual(result.returncode, 1)
                self.assertIn('re-run hunks', result.stderr)
        self.assertEqual(self.git('diff', '--cached'), '')

    def test_commit_prints_hash_and_subject(self):
        self.write('app.txt', BASE + 'more\n')
        self.git('add', 'app.txt')
        result = self.run_script('commit', input='feat: add more\n\nBody line.\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.git('log', '-1', '--format=%h feat: add more'))
        self.assertEqual(self.git('log', '-1', '--format=%B'), 'feat: add more\n\nBody line.\n\n')

    def test_commit_blocked_by_lint(self):
        self.write('app.txt', BASE + 'more\n')
        self.git('add', 'app.txt')
        self.write('msg', 'Added more\n')
        result = self.run_script('commit', 'msg')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), '1')
        self.assertEqual(self.run_script('commit', 'msg', '--skip-lint').returncode, 0)

    def test_commit_requires_staged_changes(self):
        self.write('msg', 'feat: add more\n')
        result = self.run_script('commit', 'msg')
        self.assertEqual(result.returncode, 1)
        self.assertIn('nothing staged', result.stderr)

    def test_commit_detects_hook_changes(self):
        hook = self.repo / '.git' / 'hooks' / 'pre-commit'
        hook.write_text('#!/bin/sh\necho hooked >> app.txt\ngit add app.txt\n')
        hook.chmod(0o755)
        self.write('app.txt', BASE + 'more\n')
        self.git('add', 'app.txt')
        self.write('msg', 'feat: add more\n')
        result = self.run_script('commit', 'msg')
        self.assertEqual(result.returncode, 3)
        self.assertIn('commit created', result.stderr)
        self.assertEqual(self.git('rev-list', '--count', 'HEAD').strip(), '2')


if __name__ == '__main__':
    unittest.main()
