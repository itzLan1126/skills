"""Agent Skills specification checks: https://agentskills.io/specification"""
from pathlib import Path
import re
import tempfile
import unittest

import strictyaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'skills'
FIELDS = {'name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools'}
NAME = re.compile(r'[a-z0-9]+(-[a-z0-9]+)*')
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
MAX_LINES = 500


def spec_errors(skill_dir):
    path = skill_dir / 'SKILL.md'
    if not path.is_file():
        return ['missing SKILL.md']
    lines = path.read_text(encoding='utf-8').splitlines()
    if not lines or lines[0] != '---':
        return ['SKILL.md must start with --- frontmatter']
    try:
        end = lines.index('---', 1)
    except ValueError:
        return ['frontmatter is not closed with ---']
    try:
        meta = strictyaml.load('\n'.join(lines[1:end])).data
    except strictyaml.YAMLError as error:
        return [f'invalid frontmatter YAML: {error}']
    if not isinstance(meta, dict):
        return ['frontmatter must be a mapping']

    errors = [f'unexpected field: {key}' for key in sorted(set(meta) - FIELDS)]
    name = meta.get('name')
    if not isinstance(name, str) or len(name) > MAX_NAME or not NAME.fullmatch(name):
        errors.append(f'missing or invalid name: {name!r}')
    elif name != skill_dir.name:
        errors.append(f'name {name!r} does not match directory {skill_dir.name!r}')
    for field, limit in (('description', MAX_DESCRIPTION), ('compatibility', MAX_COMPATIBILITY)):
        if field == 'compatibility' and field not in meta:
            continue
        value = meta.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            errors.append(f'{field} must be 1-{limit} characters')
    if 'metadata' in meta:
        metadata = meta['metadata']
        if not isinstance(metadata, dict) or not all(isinstance(v, str) for v in metadata.values()):
            errors.append('metadata must map strings to strings')
    if 'allowed-tools' in meta and not isinstance(meta['allowed-tools'], str):
        errors.append('allowed-tools must be a space-separated string')
    if len(lines) > MAX_LINES:
        errors.append(f'SKILL.md has {len(lines)} lines; keep it under {MAX_LINES}')
    return errors


VALID = 'name: demo\ndescription: Demo skill. Use when testing.\n'


class Spec(unittest.TestCase):
    def test_all_skills(self):
        self.assertTrue(SKILLS.is_dir(), 'missing skills directory')
        for skill in sorted(SKILLS.iterdir()):
            if skill.is_dir():
                with self.subTest(skill=skill.name):
                    self.assertEqual(spec_errors(skill), [])

    def errors_for(self, text, directory='demo'):
        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / directory
            skill.mkdir()
            if text is not None:
                (skill / 'SKILL.md').write_text(text, encoding='utf-8')
            return spec_errors(skill)

    def test_valid_optional_fields(self):
        text = (f'---\n{VALID}license: MIT\ncompatibility: Requires Python 3.11+\n'
                'metadata:\n  author: example\n  version: "1.0"\nallowed-tools: Bash(git:*) Read\n---\nBody\n')
        self.assertEqual(self.errors_for(text), [])

    def test_valid_boundaries(self):
        for length in (1, MAX_NAME):
            name = 'a' * length
            with self.subTest(field='name', length=length):
                text = f'---\nname: {name}\ndescription: Demo.\n---\n'
                self.assertEqual(self.errors_for(text, directory=name), [])
        for length in (1, MAX_DESCRIPTION):
            with self.subTest(field='description', length=length):
                text = f'---\nname: demo\ndescription: {"中" * length}\n---\n'
                self.assertEqual(self.errors_for(text), [])
        for length in (1, MAX_COMPATIBILITY):
            with self.subTest(field='compatibility', length=length):
                text = f'---\n{VALID}compatibility: {"a" * length}\n---\n'
                self.assertEqual(self.errors_for(text), [])
        text = f'---\n{VALID}---\n'
        text += 'line\n' * (MAX_LINES - len(text.splitlines()))
        self.assertEqual(self.errors_for(text), [])

    def test_rejects_invalid_skills(self):
        cases = [
            (None, 'missing SKILL.md'),
            ('', 'must start with'),
            ('Body only\n', 'must start with'),
            (f'---\n{VALID}', 'not closed'),
            (f'---\n{VALID}name: other\n---\n', 'invalid frontmatter YAML'),
            ('---\ndescription: "unterminated\n---\n', 'invalid frontmatter YAML'),
            ('---\n- name\n- description\n---\n', 'must be a mapping'),
            (f'---\n{VALID}version: "1"\n---\n', 'unexpected field: version'),
            ('---\ndescription: Demo.\n---\n', 'missing or invalid name'),
            *[(f'---\nname: {name}\ndescription: Demo.\n---\n', 'missing or invalid name')
              for name in ('Style', '-style', 'style-', 'st--yle', 'st_yle', 'a' * (MAX_NAME + 1))],
            ('---\nname: demo\n---\n', 'description must be'),
            ('---\nname: demo\ndescription:\n---\n', 'description must be'),
            ('---\nname: demo\ndescription: "   "\n---\n', 'description must be'),
            ('---\nname: demo\ndescription:\n  - Demo\n---\n', 'description must be'),
            (f'---\nname: demo\ndescription: {"a" * (MAX_DESCRIPTION + 1)}\n---\n', 'description must be'),
            (f'---\n{VALID}compatibility:\n---\n', 'compatibility must be'),
            (f'---\n{VALID}compatibility: "   "\n---\n', 'compatibility must be'),
            (f'---\n{VALID}compatibility:\n  - Python\n---\n', 'compatibility must be'),
            (f'---\n{VALID}compatibility: {"a" * (MAX_COMPATIBILITY + 1)}\n---\n', 'compatibility must be'),
            (f'---\n{VALID}metadata: plain\n---\n', 'metadata must map'),
            (f'---\n{VALID}metadata:\n  tags:\n    - a\n---\n', 'metadata must map'),
            (f'---\n{VALID}allowed-tools:\n  - Read\n---\n', 'allowed-tools must be'),
            (f'---\n{VALID}---\n' + 'line\n' * (MAX_LINES - 3), 'keep it under'),
        ]
        for index, (text, expected) in enumerate(cases):
            with self.subTest(case=index, text=text and text[:60], expected=expected):
                errors = self.errors_for(text)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_rejects_directory_mismatch(self):
        errors = self.errors_for(f'---\n{VALID}---\n', directory='other')
        self.assertEqual(errors, ["name 'demo' does not match directory 'other'"])


if __name__ == '__main__':
    unittest.main()