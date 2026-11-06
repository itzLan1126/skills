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
  "pr view") printf '%s\\tfeat\\tfalse\\n' "$FAKE_GH_STATE" ;;
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

    def run_script(self, state):
        return subprocess.run(['bash', str(SCRIPT), '#7'], cwd=self.work, capture_output=True, text=True,
                              env={**self.env, 'FAKE_GH_STATE': state})

    def git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.work, capture_output=True, text=True).stdout

    def test_merged_cleans_up(self):
        result = self.run_script('MERGED')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('remote branch: deleted', result.stdout)
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


if __name__ == '__main__':
    unittest.main()
