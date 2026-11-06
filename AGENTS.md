# AGENTS.md

This repo contains personal skills in the [Agent Skills](https://agentskills.io/specification) format.

## Layout

| Item        | Location                    |
| ----------- | --------------------------- |
| Skill entry | `skills/<name>/SKILL.md`    |
| References  | `skills/<name>/references/` |
| Scripts     | `skills/<name>/scripts/`    |
| Tests       | `tests/`                    |

## Skill Preferences

- **Intent vs. Execution**: Use AI to interpret intent and context (e.g., identify target PR from conversation). Prefer deterministic tools (scripts, CLIs, tests, linters) for execution and validation.
- **Scripts**: Put deterministic steps in `scripts/`, invoke them with relative paths, and add behavior tests in `tests/`.
- **Links**: Keep every relative file path valid (unverified by tests).
- **Spec**: `tests/test_spec.py` is the source of truth for naming, frontmatter, and length rules. Read it before authoring a skill.

## Verification

After adding or modifying a skill, run tests until they pass:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

If `.venv` is missing, initialize it first:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
