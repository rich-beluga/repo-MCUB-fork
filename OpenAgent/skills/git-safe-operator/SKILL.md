---
name: git-safe-operator
description: Inspect git status, diffs, branches, and prepare commits safely while preserving unrelated user changes.
keywords:
  - git
  - status
  - diff
  - commit
  - branch
  - stash
  - changes
  - repo
  - коммит
  - дифф
---

# Git Safe Operator

Use this skill when the user asks to inspect repository state, summarize diffs, prepare a commit, manage branches, or reason about git changes.

## Main goal

Protect user work. Inspect before acting, separate current-task changes from unrelated modifications, and never commit, push, reset, clean, or discard changes without explicit user instruction.

## Standard workflow

1. Run read-only inspection first:
   - `git status --short`;
   - `git diff --name-only` or `git diff --stat`;
   - targeted `git diff -- <path>` when needed.
2. Identify files changed by the current task versus pre-existing or unrelated changes.
3. Stage only requested/current-task files if a commit is explicitly requested.
4. Use explicit non-interactive commands such as `git commit -m "message"` only after approval.
5. Report branch, changed files, and any untracked or unrelated work left untouched.

## Diff review rules

- Prefer targeted diffs over huge repository-wide dumps.
- Summarize behavior changes, not just line counts.
- Call out risky changes: secrets, generated files, lockfiles, migrations, destructive scripts, public API changes.
- If reviewing for release, combine with the relevant project-specific audit skill.

## Commit message guidance

When asked to prepare a commit message:

- Use imperative mood: `Add ...`, `Fix ...`, `Update ...`.
- Keep the subject concise.
- Mention tests in the body when useful.
- Do not include secrets, private URLs, or noisy tool output.

## Safety rules

- Do not run `git reset`, `git clean`, force-push, rebase, or destructive checkout unless explicitly requested and confirmed.
- Do not include unrelated working-tree changes in commits.
- Do not bypass hooks unless the user explicitly asks and accepts the risk.
- Do not push without explicit user request.
- Avoid pagers; use `--no-pager` or commands that print directly.
