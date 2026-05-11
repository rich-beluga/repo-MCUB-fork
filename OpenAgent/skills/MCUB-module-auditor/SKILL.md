---
name: MCUB-module-auditor
description: Statically audit MCUB modules before release for safety, metadata, dependencies, commands, inline callbacks, and release readiness without editing code.
keywords:
  - audit
  - review
  - static
  - release
  - safety
  - secrets
  - dependencies
  - commands
  - inline
  - callbacks
  - hikka
  - аудит
  - проверка
---

# MCUB Module Auditor

Use this skill when the user asks to audit, review, inspect, or assess an MCUB module before release without changing module code.

## Main goal

Statically review MCUB userbot modules for safety, MCUB compatibility, metadata completeness, dependency clarity, command and inline callback readiness, and release blockers.

This skill is audit-only. Recommend checks and fixes, but do not edit module files and do not publish releases.

## Core rules

- Read and analyze only; do not edit the audited module or unrelated files.
- MCUB modules are **MCUB userbot modules**, not Hikka modules and not regular Telegram Bot API bots.
- Treat safety issues as release blockers until explained or removed.
- Prefer concrete file/line findings over generic advice.
- Do not assume Hikka conventions are acceptable in MCUB modules.
- Recommend syntax check and MCUB debugger validation, but keep this workflow static unless the user separately asks to run tools.

## Standard workflow

1. Identify the target module file and its intended release name.
2. Read the module fully before judging it.
3. Review safety-sensitive code first: secrets, network calls, filesystem/shell use, dynamic execution, and obfuscation.
4. Review MCUB API style and flag Hikka-style patterns.
5. Review metadata, dependencies, commands, callbacks, config, storage, and lifecycle behavior.
6. Summarize blockers, warnings, and recommended actions.
7. End with one release readiness state: `READY`, `READY WITH WARNINGS`, or `BLOCKED`.

## Audit checklist

### Safety and secrets

- Check for hardcoded tokens, API keys, session strings, phone numbers, credentials, and private URLs.
- Flag obfuscation, hidden payloads, suspicious encoding, network exfiltration, and telemetry without clear user value.
- Flag destructive filesystem operations, arbitrary file deletion/overwrite, unsafe shell calls, and untrusted path handling.
- Flag arbitrary `exec`, `eval`, dynamic imports, unsafe `subprocess`, `os.system`, and command execution from user input.

### MCUB style and Hikka mismatch

- Expected MCUB style includes imports from `core.lib.loader.module_base`, `loader.ModuleBase`, and `@loader.command` / `@loader.callback` patterns.
- Flag Hikka-style imports such as `from .. import utils, loader` and base classes such as `loader.Module`.
- Flag Hikka-only assumptions, helpers, or `strings` name-only conventions as insufficient for MCUB release readiness.

### Metadata and documentation

- Check `name`, `version`, `author`, and `description` metadata.
- Check localized docs/descriptions when the module is user-facing.
- Check dependency metadata for every external library import.
- Verify commands have clear registration and useful docstrings/help text.

### Commands, inline, config, and storage

- Review command names, permissions, argument handling, user feedback, and error paths.
- Review inline forms, callback data, callback permissions, and callback routing.
- Check config defaults for safe values and no embedded secrets.
- Check database/cache use for namespacing, cleanup, and safe persistence.
- Check lifecycle hooks for startup/shutdown behavior and cleanup of loops, tasks, clients, temp files, and cache.

## Release readiness output

Report concisely with these fields:

- `Status`: `READY`, `READY WITH WARNINGS`, or `BLOCKED`.
- `Blockers`: issues that must be fixed before release.
- `Warnings`: non-blocking risks or cleanup recommendations.
- `Actions`: concrete recommended fixes or validation steps.
- `Validation`: recommend `python -m py_compile <module.py>` and `python -m debugger.cli <module.py>` when appropriate.

Use `READY` only when no safety or compatibility blockers are found. Use `READY WITH WARNINGS` when release is plausible but improvements or manual confirmations remain. Use `BLOCKED` for secrets, destructive behavior, suspicious execution/exfiltration, syntax-breaking structure, or clear non-MCUB/Hikka implementation patterns.

## Safety rules

- Do not edit, format, copy, release, commit, or push audited module files.
- Do not expose discovered secrets in the response; identify the key/location and say it must be removed or rotated.
- Do not approve suspicious, obfuscated, destructive, or arbitrary-execution code for release.
- Do not convert the audit into publishing; use the release workflow only if the user explicitly asks after audit findings are resolved.
