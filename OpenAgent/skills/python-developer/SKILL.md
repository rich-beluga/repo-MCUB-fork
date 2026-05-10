---
name: python-developer
description: Write, review, debug, and refactor Python code with project-aware style, tests, async safety, and clean error handling.
keywords:
  - python
  - питон
  - python3
  - py
  - asyncio
  - pytest
  - typing
  - refactor
  - debug
  - traceback
---

# Python Developer

Use this skill when the user asks to create, fix, review, refactor, test, or explain Python code.

This skill is general-purpose Python guidance for OpenAgent. For MCUB modules, combine it with the MCUB-specific skills and let the MCUB conventions win when there is a conflict.

## Core workflow

1. Identify the exact Python runtime context before editing:
   - script, package, library module, userbot module, test, CLI, or service;
   - synchronous or asynchronous execution;
   - existing dependency and style constraints.
2. Inspect nearby code before proposing changes.
3. Prefer the smallest safe change that solves the request.
4. Preserve public APIs, file layout, command names, config keys, and persisted data formats unless the user explicitly asks to change them.
5. Validate with the narrowest useful command first, then broaden only when needed.

## Code style rules

- Use clear Python 3 code with explicit names and simple control flow.
- Prefer standard-library solutions unless the repository already depends on a third-party package or the user approves adding one.
- Keep functions focused; split large functions only when it improves readability without changing behavior.
- Use type hints when they clarify interfaces, but do not perform noisy whole-file typing rewrites.
- Use dataclasses or small typed containers for structured data when dictionaries become unclear.
- Avoid clever metaprogramming, hidden global state, import side effects, and broad monkey-patching.
- Do not hardcode secrets, tokens, phone numbers, API keys, session strings, or credentials.

## Error handling

- Catch specific exceptions, not bare `except`.
- Preserve tracebacks for unexpected errors unless user-facing output requires a clean message.
- Add context to errors without swallowing the root cause.
- Avoid silent fallback behavior unless the existing project style already uses it and the fallback is safe.

## Async Python rules

- Use `async`/`await` consistently; do not block the event loop with long synchronous work.
- Avoid `asyncio.run()` inside an already-running async application.
- Prefer existing task/session/client lifecycle management instead of creating ad-hoc globals.
- For network or Telegram-style code, consider cancellation, timeout, and cleanup paths.

## Testing and validation

Choose validation based on the change:

- syntax-only change: `python -m py_compile <file>`;
- focused unit change: run the nearest pytest test file or targeted test;
- package-level behavior: run the relevant project test command;
- JSON/config edits: validate with the appropriate parser.

When tests fail, report the failing command and fix only failures caused by the current change.

## Debugging workflow

When given a traceback or failing behavior:

1. Locate the first project-owned frame related to the failure.
2. Explain the likely root cause in one or two sentences.
3. Patch the cause, not just the symptom.
4. Add or update a focused regression test when the repository has a matching test pattern.

## MCUB-specific note

MCUB is a Telethon-based userbot project. When editing MCUB modules or release workflows:

- do not assume Hikka APIs or Hikka module patterns;
- follow `MCUB-modules-creator` for module code;
- follow `MCUB-release-modules` for publishing and repository commits;
- keep generated Python compatible with the existing MCUB runtime and debugger rules.
