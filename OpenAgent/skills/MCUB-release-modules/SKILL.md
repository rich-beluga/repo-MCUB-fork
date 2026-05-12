---
name: MCUB-release-modules
description: Validate, publish, index, commit, and push MCUB modules from debug builds into the MCUB module repository.
keywords:
  - release
  - publish
  - peлиз
  - выпycти
  - oпyбликyй
  - repo-MCUB-fork
  - modules.ini
  - commit
  - push
---

# MCUB Release Modules

Use this skill when the user asks to release, publish, upload, ship, or update an MCUB module in the public MCUB module repository.

This skill is for moving an already-created MCUB module from the MCUB-fork/debug workspace into the release repository:

```text
/home/alina/test/MCUB/repo-MCUB-fork/
```

## Core rules

- MCUB modules are **MCUB userbot modules**, not Hikka modules and not regular Telegram Bot API bots.
- Release only modules that use the MCUB API correctly.
- Before release, always validate the module with:
  1. Python syntax check.
  2. MCUB debugger.
- Do not release modules with syntax errors or debugger errors.
- Do not hardcode secrets, tokens, API keys, session strings, phone numbers, or credentials.
- Do not publish suspicious code, obfuscated code, destructive code, or code that executes arbitrary shell/Python from untrusted input.

## Source and destination

Typical source module:

```text
/home/alina/test/MCUB/MCUB-fork/app-debug/{module-name}/modules-debug-v{version}.py
```

Release destination:

```text
/home/alina/test/MCUB/repo-MCUB-fork/{name-modules}-MCUB-repo.py
```

The released file name must be the canonical module repository name.

Examples:

```text
Weather-MCUB-repo.py
speedtest-MCUB-repo.py
menu-buttons-MCUB-repo.py
```

## modules.ini rule

The module must be listed in:

```text
/home/alina/test/MCUB/repo-MCUB-fork/modules.ini
```

The `modules.ini` entry must match the released file name **without `.py`** exactly.

Example:

```text
speedtest-MCUB-repo.py   -> modules.ini entry: speedtest-MCUB-repo
Weather-MCUB-repo.py     -> modules.ini entry: Weather-MCUB-repo
```

Rules:

- Do not add `.py` in `modules.ini`.
- Do not add duplicate entries.
- Preserve existing entries.
- For a new module, append the exact module name if it is missing.
- For an update to an existing module, verify the matching entry already exists; add it only if missing.

## Required validation workflow

Before copying/moving the module to the release repository:

1. Locate the source `.py` module.
2. Confirm it is the intended build/version.
3. Run syntax check from the MCUB-fork repository root:

```bash
python -m py_compile app-debug/{module-name}/modules-debug-v{version}.py
```

4. Run MCUB debugger from the MCUB-fork repository root:

```bash
python -m debugger.cli app-debug/{module-name}/modules-debug-v{version}.py
```

5. Treat debugger errors as blockers.
6. Fix warnings when they indicate real MCUB runtime issues.
7. If a debugger warning is intentionally safe, mention it in the final response.

If the source module is outside `app-debug/`, still run the same checks against its actual path.

## Release workflow: new module

Use this workflow when the module is not already present in `/home/alina/test/MCUB/repo-MCUB-fork/`.

1. Validate source module syntax.
2. Validate source module with MCUB debugger.
3. Determine release file name:

```text
{name-modules}-MCUB-repo.py
```

4. Copy the validated module into:

```text
/home/alina/test/MCUB/repo-MCUB-fork/{name-modules}-MCUB-repo.py
```

5. Verify the copied file exists and matches the intended module.
6. Commit the module file in the release repository.
7. Add the module name to `modules.ini` exactly as the file name without `.py`.
8. Commit the `modules.ini` change separately.
9. Push the release repository.

Recommended commit structure:

```text
add {name-modules} module
add {name-modules} to modules index
```

## Release workflow: updating an existing module

Use this workflow when `/home/alina/test/MCUB/repo-MCUB-fork/{name-modules}-MCUB-repo.py` already exists.

1. Validate the new source module syntax.
2. Validate the new source module with MCUB debugger.
3. Replace/update the existing release file with the validated source content.
4. Verify the release file name remains unchanged:

```text
{name-modules}-MCUB-repo.py
```

5. Commit the updated module file.
6. Verify `modules.ini` contains the exact entry `{name-modules}-MCUB-repo`.
7. If `modules.ini` was missing the entry, add it and commit that change separately.
8. Push the release repository.

Recommended commit structure:

```text
update {name-modules} module
add {name-modules} to modules index
```

Only create the second commit if `modules.ini` actually changed.

## Git workflow requirements

All git operations for release happen in:

```text
/home/alina/test/MCUB/repo-MCUB-fork
```

Before committing:

1. Run `git status --short`.
2. Run `git diff --no-pager` for unstaged changes.
3. Ensure only intended release files are included:
   - `{name-modules}-MCUB-repo.py`
   - `modules.ini` if it changed.
4. Do not commit unrelated files.
5. Do not commit secrets or local config files.

Commit sequence for new module:

```bash
git add {name-modules}-MCUB-repo.py
git commit -m "add {name-modules} module"
git add modules.ini
git commit -m "add {name-modules} to modules index"
git push
```

Commit sequence for update:

```bash
git add {name-modules}-MCUB-repo.py
git commit -m "update {name-modules} module"
# only if modules.ini changed:
git add modules.ini
git commit -m "add {name-modules} to modules index"
git push
```

If there are no changes after validation, do not create an empty commit. Tell the user the module is already up to date.

## File naming checks

Before committing, verify:

- Release file path is exactly:

```text
/home/alina/test/MCUB/repo-MCUB-fork/{name-modules}-MCUB-repo.py
```

- `modules.ini` contains exactly:

```text
{name-modules}-MCUB-repo
```

- The `modules.ini` entry and release file basename match exactly:

```python
Path(file).stem == modules_ini_entry
```

## Verification after release

After committing and pushing:

1. Run `git status --short` in `/home/alina/test/MCUB/repo-MCUB-fork`.
2. Confirm the branch is clean or only has unrelated pre-existing changes that were intentionally not touched.
3. Report:
   - source file used;
   - released file path;
   - syntax check result;
   - debugger result;
   - module commit hash;
   - modules.ini commit hash if created;
   - push result.

## Do not do

- Do not skip syntax validation.
- Do not skip MCUB debugger validation.
- Do not release Hikka modules as MCUB modules.
- Do not let `modules.ini` use a name different from the release file stem.
- Do not add `.py` to `modules.ini`.
- Do not commit unrelated files.
- Do not push from the MCUB-fork repo when the release target is `repo-MCUB-fork`.
- Do not force push unless the user explicitly requests it and understands the risk.
