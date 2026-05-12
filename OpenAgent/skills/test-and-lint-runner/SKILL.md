---
name: test-and-lint-runner
description: Choose and run focused tests, lint, type checks, syntax checks, and builds safely in non-interactive project environments.
keywords:
  - test
  - tests
  - pytest
  - lint
  - build
  - typecheck
  - ruff
  - eslint
  - vitest
  - пpoвepкa
---

# Test and Lint Runner

Use this skill when the user asks to run checks, verify a change, diagnose failing tests, or decide which validation command is appropriate.

## Main goal

Validate changes with the smallest useful non-interactive command first, then broaden only when needed. Report exact commands, results, and remaining failures without hiding output that matters.

## Discovery workflow

1. Inspect project files for check commands:
   - `package.json` scripts;
   - `pyproject.toml`, `tox.ini`, `pytest.ini`, `ruff.toml`, `.eslintrc*`, `tsconfig.json`;
   - README or project docs when commands are not obvious.
2. Match checks to the changed files and language.
3. Prefer focused checks over full suites for fast feedback.
4. Use timeouts for long-running commands.
5. If a command fails, identify whether the failure is caused by the current change before fixing anything.

## Command selection

Python examples:

- Syntax: `python -m py_compile path/to/file.py`.
- Focused tests: `python -m pytest path/to/test_file.py -q`.
- Lint: project-specific `ruff`, `flake8`, or configured command.

JavaScript/TypeScript examples:

- Package scripts from `package.json` first.
- Type-check: existing `typecheck` script or configured compiler command.
- Tests: focused test command if the framework supports it.
- Build: run only when needed or requested.

MCUB examples:

- Module syntax: `python -m py_compile app-debug/.../modules-debug-vX.Y.Z.py`.
- Debugger: `python -m debugger.cli path/to/module.py` when debugger validation is relevant.

## Failure handling

- Preserve the failing command and concise error summary.
- Fix only failures caused by the current task.
- Do not chase unrelated flaky tests or pre-existing repository failures unless the user asks.
- If the failure is environmental, report the missing tool, dependency, path, or service.

## Safety rules

- Never run interactive watch modes as validation.
- Do not use prompts, pagers, REPLs, or commands that wait for input.
- Do not install dependencies automatically unless the user asked for setup.
- Do not expose secrets from test logs; mask them in summaries.
