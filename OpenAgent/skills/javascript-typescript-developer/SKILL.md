---
name: javascript-typescript-developer
description: Build, debug, refactor, and type-check JavaScript and TypeScript code using project conventions and minimal dependencies.
keywords:
  - javascript
  - typescript
  - js
  - ts
  - node
  - npm
  - pnpm
  - yarn
  - frontend
  - react
  - типы
---

# JavaScript/TypeScript Developer

Use this skill when the user asks to create, fix, refactor, review, or explain JavaScript or TypeScript code.

## Core workflow

1. Detect the project runtime and package manager from existing files: `package.json`, lockfiles, config files, and nearby source.
2. Inspect similar code before editing.
3. Make the smallest safe change that preserves public APIs, exports, route names, config keys, and persisted formats.
4. Prefer existing dependencies and utilities over adding new packages.
5. Validate with the narrowest useful command: type-check, lint, focused test, or build.

## TypeScript rules

- Prefer precise types and existing project type aliases.
- Avoid `any`; if unavoidable, keep it local and explain why.
- Do not weaken exported types to hide errors.
- Preserve module boundaries and import style used by the project.
- Keep async flows explicit and handle rejected promises where callers cannot reasonably handle them.

## JavaScript rules

- Use modern syntax supported by the configured runtime.
- Keep functions small and names descriptive.
- Avoid hidden global state, import side effects, and broad monkey-patching.
- Add JSDoc only when it improves readability or matches local style.

## Package manager safety

Use the existing package manager:

- `npm` when `package-lock.json` exists.
- `pnpm` when `pnpm-lock.yaml` exists.
- `yarn` when `yarn.lock` exists.
- `bun` when `bun.lockb` or `bun.lock` exists.

Run commands non-interactively and avoid dependency changes unless necessary and approved.

## Validation examples

- Syntax or small file check: project-specific lint/type command.
- TypeScript: `npm run typecheck` or the existing equivalent.
- Tests: focused test first, then broader suite if needed.
- Build-sensitive changes: run the project build command when available.

## Safety rules

- Do not commit, publish, or install new dependencies without explicit user intent.
- Do not expose tokens, API keys, `.env` values, or private endpoints.
- Do not rewrite unrelated formatting or generated files.
- If MCUB module code is involved, follow MCUB-specific skills instead of generic JS assumptions.
