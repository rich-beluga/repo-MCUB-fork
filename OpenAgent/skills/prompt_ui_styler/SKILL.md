---
name: prompt_ui_styler
description: Adjust OpenAgent appearance, answer layout, thinking/status text, emojis, labels, templates, and config UI safely.
keywords:
  - prompt
  - ui
  - style
  - template
  - внешний вид
  - оформление
  - thinking
  - emoji
  - label
  - placeholders
---

# Prompt/UI Styler

Use this skill when the user asks to change OpenAgent appearance, answer layout, thinking/status text, emojis, labels, templates, placeholders, or module config UI.

## Main goal

Style OpenAgent safely through config whenever possible. Prefer changing existing OpenAgent config values instead of editing source code.

## Useful OpenAgent config keys

- `response_header` — final answer header template.
- `request_label` — label before the user prompt block.
- `response_label` — label before the answer block.
- `thinking_template` — initial loading/thinking message.
- `tool_display_template` — template shown while tools run.
- `tool_status_emojis` — emoji/icon mapping for tool groups and exact tool names.
- `thinking_display_limit` — how many recent `thinking.note` lines to show.
- `thinking_empty_text` — text used when there are no thinking notes.
- `thinking_bullet` — marker before every thinking note line. Examples: `•`, `-`, `👉`, `➤`, or empty to disable the marker.
- `random_strings` — random lines used by `{random}`.
- `placeholders` — generated help text with available placeholders.

## How to inspect key values safely

When the user asks “посмотри значение”, “какие ключи”, “что сейчас стоит”, or similar:

1. Read/inspect the current value first.
2. Report the value clearly, but mask secrets.
3. Do **not** change anything unless the user explicitly asked to change it.

Preferred ways:

- Use `.cfg OpenAgent` or the MCUB config tool when available.
- Use `utility.placeholders` when the user asks about placeholders/templates.
- Use `skills.read` only for reading saved skill markdown.
- For code defaults, read `OpenAgent-MCUB-repo.py` and inspect `ModuleConfig` / `defaults`.

Safety rules:

- Never reveal raw secret values like `api_key`.
- For secret keys, say only: set / empty / looks configured.
- Never rewrite a config key just because you inspected it.
- Only change a key when the user clearly says: “поменяй”, “установи”, “сделай значение”, “замени”, “set”, “change”, etc.

## Change workflow

1. Identify the exact config key that controls the requested UI detail.
2. If useful, show the current value.
3. Apply only the requested key change.
4. Explain how to revert.

Examples:

- “сделай точку в thinking как стрелку” → set `thinking_bullet` to `➤`.
- “убери точку перед thinking” → set `thinking_bullet` to empty string.
- “покажи какие плейсхолдеры есть” → use `utility.placeholders`; do not change anything.
- “что в response_header?” → read/report `response_header`; do not change it.
- “поменяй response_header на ...” → update only `response_header`.

## Template placeholders

Common placeholders:

- `{provider}`, `{provider_key}`, `{model}`
- `{elapsed}`, `{tool_count}`
- `{input_tokens}`, `{output_tokens}`, `{total_tokens}`
- `{thinking}` — recent thinking notes formatted with `thinking_bullet`
- `{random}` — random string from `random_strings`
- `{prefix}`, `{time}`, `{date}`

For `tool_display_template`, useful extra placeholders:

- `{status_emoji}`, `{status_icon}`, `{status_text}`
- `{tool_group}`, `{tool_short}`
- `{tool_input}`, `{tool_input_block}`
- `{thinking_line}`, `{thinking_block}`
- `{log_lines}`, `{log_block}`
- `{round}`, `{round_total}`, `{progress_bar}`, `{progress_percent}`

## Style recommendations

- Keep Telegram HTML valid: `<b>`, `<i>`, `<code>`, `<blockquote expandable>`.
- Keep templates short enough for Telegram limits.
- Use `thinking_bullet` for marker changes instead of editing code.
- Use `tool_status_emojis` for tool icons instead of editing code.

## Never do

- Do not change API keys, provider, model, timeout, or behavior config unless the user explicitly asks.
- Do not expose secret values.
- Do not overwrite multiple style keys for one small request.
- Do not edit source code for a style change that already has a config key.
