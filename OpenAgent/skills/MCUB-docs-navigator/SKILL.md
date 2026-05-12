---
name: MCUB-docs-navigator
description: Navigate and explain local MCUB documentation while routing module and API questions to the right sources and warning against Hikka assumptions.
keywords:
  - docs
  - documentation
  - doc
  - API_DOC.md
  - mcub
  - api
  - module
  - modules
  - hikka
  - cпpaвкa
  - дoкyмeнтaция
---

# MCUB Docs Navigator

Use this skill when the user asks to find, read, explain, or cross-reference local MCUB documentation, API guides, module docs, inline docs, or examples.

## Main goal

Answer MCUB documentation questions from local project sources first, with precise file paths and clear routing to the correct MCUB workflow when the question becomes implementation, debugging, or release work.

## Primary sources

Start with these local documents when present:

- `API_DOC.md` for the documentation index and API overview.
- `doc/registration/class-style.md` for class-style modules.
- `doc/guides/module-structure.md` and `doc/guides/best-practices.md` for module layout and conventions.
- `doc/inline/inline-form.md` and `doc/inline/callbacks.md` for inline forms and callbacks.
- `doc/api/module-config.md`, `doc/api/database.md`, and `doc/api/errors.md` for config, persistence, and error handling.
- Existing modules under `app-debug/` or release module folders only as examples, not as documentation authority.

## Workflow

1. Identify the documentation topic and likely source file.
2. Read the closest local docs before answering.
3. Quote or summarize only the relevant section; avoid dumping long files.
4. Include exact paths so the user can inspect the source.
5. If docs conflict with code, say so and recommend verifying against current implementation.
6. Route follow-up implementation to `MCUB-modules-creator`, debugger fixes to `MCUB-debugger-fixer`, audits to `MCUB-module-auditor`, and releases to `MCUB-release-modules`.

## MCUB-specific rules

- MCUB modules are not Hikka modules.
- Do not answer MCUB API questions using Hikka imports, base classes, or registration patterns.
- Treat MCUB as a Telethon-based userbot unless docs explicitly discuss the auxiliary bot layer.
- Prefer documented MCUB helpers such as `ModuleBase`, `@loader.command`, `self.edit`, `self.answer`, `self.db`, `self.cache`, and inline callback APIs when the docs support them.

## Response style

Keep answers practical:

- `Source`: path(s) used.
- `Answer`: concise explanation.
- `Use this when coding`: short actionable notes.
- `Next workflow`: name the skill to use if the user wants code changes.

## Safety rules

- Do not invent undocumented MCUB APIs.
- Do not expose secrets from examples or runtime config.
- Do not edit files in this docs-only workflow unless the user explicitly asks to update documentation.
