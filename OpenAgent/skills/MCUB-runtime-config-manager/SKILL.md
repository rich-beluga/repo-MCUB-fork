---
name: MCUB-runtime-config-manager
description: Safely inspect and manage MCUB runtime configuration, prefixes, aliases, trusted users, access rules, and backups with secret masking and confirmations.
keywords:
  - cfg
  - fcfg
  - setprefix
  - aliases
  - trusted
  - access
  - backup
  - config
  - settings
  - secrets
  - runtime
  - префикс
  - конфиг
---

# MCUB Runtime Config Manager

Use this skill when the user asks to inspect or change MCUB runtime settings through commands such as `cfg`, `fcfg`, `setprefix`, `aliases`, `trusted`, `access`, `backup`, or restore operations.

## Main goal

Safely manage MCUB runtime configuration without leaking secrets or accidentally weakening access controls. Prefer read-only inspection first, backup before mutation, verification after mutation, and a concise record of old/new non-secret state.

## Core rules

- MCUB is a Telegram userbot; prefix, trusted-user, and access changes affect user-account automation.
- Guide runtime configuration actions; do not edit source files or config stores directly unless the user explicitly asks and a safe workflow exists.
- Use `Mcub-commander` for actual command execution or command explanation when needed.
- Pass `mcub.command` arguments without command prefixes because `Mcub-commander` expects raw command text.
- Never print raw secrets, tokens, session strings, API keys, credentials, phone numbers, or sensitive config values.
- Summarize config by key names, value presence, type, shape, and risk level only.

## Standard workflow

1. Identify the exact runtime operation and affected scope: config key, prefix, alias, trusted user, access rule, backup, or restore target.
2. Start with read-only inspection when possible: current keys, command help, current prefix/aliases/trusted/access status, or available backups.
3. Mask sensitive values in all notes and outputs.
4. For mutations, create or recommend a backup first.
5. Ask for explicit confirmation before risky changes.
6. Execute through `Mcub-commander` when command execution is needed.
7. Verify the resulting non-secret state after mutation.
8. Report old/new non-secret state and any follow-up safety warnings.

## Command routing

- `cfg`: inspect or update regular runtime configuration; mask values and avoid broad dumps.
- `fcfg`: force configuration only after confirmation and backup, because it may override safety checks.
- `setprefix`: confirm before changing prefixes; warn about command usability and record old/new prefix shape.
- `aliases`: inspect aliases read-only first; confirm before deleting or replacing aliases.
- `trusted`: confirm before adding or removing trusted users; warn that this affects userbot control permissions.
- `access`: confirm broad or permission-expanding access changes; prefer narrow rules and verify after changes.
- `backup`: prefer backup before mutation; list backups without exposing secrets.
- `restore`: require explicit confirmation, confirm target backup, and warn that current runtime state may be overwritten.

## Validation checklist

Before acting, confirm:

- the requested operation is a runtime setting change, not module source work;
- the command target and arguments are clear;
- sensitive values are masked or omitted;
- read-only inspection was considered first;
- risky operations have explicit confirmation;
- a backup exists or the user accepted the risk of proceeding without one;
- post-change verification can be done without exposing secrets.

## Safety rules

- Require explicit confirmation before changing prefixes, adding/removing trusted users, broad access changes, deleting aliases, forcing config, restoring backups, exposing credentials, or rotating credentials.
- Do not expose raw config values even when the user asks for a dump; provide masked summaries unless a safer explicit credential workflow is available.
- Do not store secrets in chat, files, logs, examples, or final reports.
- Do not edit runtime databases, config files, or source files directly unless the user explicitly asks and the safe workflow is understood.
- Prefer narrow, reversible changes over broad access or trust changes.
- Stop and warn if a requested action could lock the user out, expose credentials, or grant broad userbot control.
