"""close-pr.sh against a temp repo, a local bare origin, and a fake gh."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills' / 'close-pr' / 'scripts' / 'close-pr.sh'
FAKE_GH = '''#!/bin/sh
echo "$*" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "pr view") printf '%s\\t%s\\t%s\\t%s\\n' "$FAKE_GH_STATE" "${FAKE_GH_BRANCH:-feat}" "${FAKE_GH_CROSS:-false}" "$FAKE_GH_HEAD" ;;
  "repo view") echo main ;;
  api*) echo false ;;
esac
'''


class ClosePrTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        bin_dir = root / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'gh').write_text(FAKE_GH)
        (bin_dir / 'gh').chmod(0o755)
        self.log = root / 'gh.log'
        self.env = {**os.environ, 'PATH': f'{bin_dir}:{os.environ["PATH"]}', 'FAKE_GH_LOG': str(self.log),
                    'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
                    'GIT_COMMITTER_EMAIL': 't@t', 'GIT_CONFIG_GLOBAL': os.devnull}
        self.origin = root / 'origin.git'
        self.work = root / 'work'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(self.origin)], check=True)
        for cmd in (['init', '-q', '-b', 'main', str(self.work)],
                    ['-C', str(self.work), 'remote', 'add', 'origin', str(self.origin)],
                    ['-C', str(self.work), 'commit', '-q', '--allow-empty', '-m', 'init'],
                    ['-C', str(self.work), 'push', '-q', '-u', 'origin', 'main'],
                    ['-C', str(self.work), 'switch', '-q', '-c', 'feat'],
                    ['-C', str(self.work), 'commit', '-q', '--allow-empty', '-m', 'feat'],
                    ['-C', str(self.work), 'push', '-q', '-u', 'origin', 'feat']):
            subprocess.run(['git', *cmd], check=True, env=self.env)
        self.head = self.git('rev-parse', 'feat').strip()

    def run_script(self, state, head=None, branch='feat', cross='false'):
        return subprocess.run(['bash', str(SCRIPT), '#7'], cwd=self.work, capture_output=True, text=True,
                              env={**self.env, 'FAKE_GH_STATE': state, 'FAKE_GH_HEAD': head or self.head,
                                   'FAKE_GH_BRANCH': branch, 'FAKE_GH_CROSS': cross})

    def git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.work, capture_output=True, text=True,
                              env=self.env, check=True).stdout

    def test_merged_cleans_up(self):
        result = self.run_script('MERGED')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('remote branch: deleted', result.stdout)
        self.assertIn(f'local branch: deleted (was {self.head[:7]}', result.stdout)
        self.assertEqual(self.git('branch', '--show-current').strip(), 'main')
        self.assertNotIn('feat', self.git('branch'))
        self.assertNotIn('feat', self.git('branch', cwd=self.origin))

    def test_closed_unmerged_cleans_up(self):
        result = self.run_script('CLOSED')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('feat', self.git('branch'))

    def test_open_stops(self):
        result = self.run_script('OPEN')
        self.assertEqual(result.returncode, 1)
        self.assertIn('still open', result.stderr)
        self.assertEqual(self.git('branch', '--show-current').strip(), 'feat')
        self.assertIn('feat', self.git('branch', cwd=self.origin))

    def test_dirty_tree_stops_before_gh(self):
        (self.work / 'new.txt').write_text('x')
        result = self.run_script('MERGED')
        self.assertEqual(result.returncode, 1)
        self.assertIn('uncommitted', result.stderr)
        self.assertFalse(self.log.exists())
        self.assertIn('feat', self.git('branch', cwd=self.origin))

    def test_commits_after_pr_head_stop(self):
        self.git('commit', '-q', '--allow-empty', '-m', 'after merge')
        result = self.run_script('MERGED')
        self.assertEqual(result.returncode, 1)
        self.assertIn('not in PR #7', result.stderr)
        self.assertIn('after merge', self.git('log', '-1', '--format=%s', 'feat'))
        self.assertIn('feat', self.git('branch', cwd=self.origin))

    def test_fork_pr_named_like_default_branch_keeps_worktree(self):
        wt = self.work.parent / 'mywt'
        self.git('switch', '-q', '-c', 'side', 'main')
        self.git('worktree', 'add', '-q', str(wt), 'main')
        self.git('commit', '-q', '--allow-empty', '-m', 'local only', cwd=wt)
        result = self.run_script('MERGED', branch='main', cross='true')
        self.assertEqual(result.returncode, 1)
        self.assertIn('stop: main is checked out in worktree', result.stderr)
        self.assertTrue(wt.exists())
        self.assertIn('local only', self.git('log', '-1', '--format=%s', 'main'))

    def test_default_branch_in_other_worktree_stops_before_changes(self):
        wt = self.work.parent / 'mywt'
        self.git('worktree', 'add', '-q', '--detach', str(wt))
        self.git('switch', '-q', 'main', cwd=wt)
        result = self.run_script('MERGED')
        self.assertEqual(result.returncode, 1)
        self.assertIn('stop: main is checked out in worktree', result.stderr)
        self.assertEqual(self.git('branch', '--show-current').strip(), 'feat')
        self.assertIn('feat', self.git('branch', cwd=self.origin))

    def test_fetches_unknown_pr_head(self):
        other = self.work.parent / 'other'
        self.git('clone', '-q', '-b', 'feat', str(self.origin), str(other))
        self.git('commit', '-q', '--allow-empty', '-m', 'suggestion', cwd=other)
        self.git('push', '-q', 'origin', 'HEAD:refs/pull/7/head', cwd=other)
        head = self.git('rev-parse', 'HEAD', cwd=other).strip()
        result = self.run_script('MERGED', head=head)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('feat', self.git('branch'))

    def add_worktree(self):
        """Move feat out of the main checkout into a linked worktree, as a Claude Code session would."""
        wt = self.work / '.claude' / 'worktrees' / 'feat'
        self.git('switch', '-q', 'main')
        self.git('worktree', 'add', '-q', str(wt), 'feat')
        (self.work / '.git' / 'info' / 'exclude').write_text('.claude/worktrees/\n')
        return wt

    def assert_untouched(self, wt):
        self.assertTrue(wt.exists())
        self.assertIn('feat', self.git('branch'))
        self.assertIn('feat', self.git('branch', cwd=self.origin))

    def test_removes_clean_worktree(self):
        wt = self.add_worktree()
        result = self.run_script('MERGED')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('worktree: removed', result.stdout)
        self.assertFalse(wt.exists())
        self.assertNotIn('feat', self.git('branch'))
        self.assertNotIn('feat', self.git('branch', cwd=self.origin))

    def test_locked_worktree_stops(self):
        wt = self.add_worktree()
        self.git('worktree', 'lock', '--reason', 'on usb drive', str(wt))
        result = self.run_script('MERGED')
        self.assertEqual(result.returncode, 1)
        self.assertIn('on usb drive', result.stderr)
        self.assert_untouched(wt)

    def test_dirty_worktree_stops(self):
        wt = self.add_worktree()
        (wt / 'scratch.txt').write_text('x')
        result = self.run_script('MERGED')
        self.assertEqual(result.returncode, 1)
        self.assertIn('cannot remove worktree', result.stderr)
        self.assert_untouched(wt)

    def test_run_inside_worktree_stops(self):
        wt = self.add_worktree()
        result = subprocess.run(['bash', str(SCRIPT), '7'], cwd=wt, capture_output=True, text=True,
                                env={**self.env, 'FAKE_GH_STATE': 'MERGED'})
        self.assertEqual(result.returncode, 1)
        self.assertIn('main checkout', result.stderr)
        self.assertFalse(self.log.exists())
        self.assert_untouched(wt)


if __name__ == '__main__':
    unittest.main()
