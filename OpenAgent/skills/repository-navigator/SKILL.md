---
name: repository-navigator
description: Quickly map unfamiliar repositories, locate files, identify stack conventions, and point code tasks to the right implementation area.
keywords:
  - repo
  - repository
  - structure
  - locate
  - find
  - architecture
  - stack
  - files
  - навигация
  - структура
---

# Repository Navigator

Use this skill when the user asks where something lives, how a repository is structured, what stack it uses, or where to implement a change.

## Main goal

Build a fast, accurate mental map of the repository before editing. Return concrete paths, nearby examples, and the safest integration point.

## Exploration workflow

1. Inspect top-level files and directories first.
2. Read project instructions when present: `README*`, `AGENTS.md`, `.opencode/skills`, docs, and contribution notes.
3. Detect stack from config files, lockfiles, imports, and test layout.
4. Search for exact terms, then for related naming variants.
5. Read nearby examples before recommending an edit location.
6. Summarize only the relevant map; avoid dumping full directory trees.

## What to report

- `Stack`: languages/frameworks/tools inferred from files.
- `Key paths`: files or directories relevant to the request.
- `Existing patterns`: examples to follow.
- `Recommended entry point`: where to make the change and why.
- `Validation`: likely command(s) to verify the change.

## Search guidance

- Use file globbing for known patterns.
- Use text search for command names, class names, route names, config keys, and user-visible strings.
- Use AST-aware search when a language pattern matters more than raw text.
- Prefer focused reads over loading large files completely.

## Safety rules

- Do not edit during pure navigation unless the user also asked for implementation.
- Do not assume framework conventions before checking local code.
- Do not ignore project-specific instructions.
- If MCUB module work is discovered, route to `MCUB-modules-creator` or related MCUB skills.
