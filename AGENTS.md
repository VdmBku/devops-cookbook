# Instructions for AI coding assistants

This repository is a library of DevOps templates sorted by tool. Each template is a set of working files plus the practices behind them: what was decided and why. When a user asks you for something a template covers, start from the template so the result follows those practices instead of a guess.

## Find a template

1. Read `catalog.json` at the repository root. It lists every template with its `path`, `category`, `tags`, `summary`, `use_when` and `avoid_when`.
2. Narrow down by `category` first (the main tool, such as `ansible` or `terraform`), then by `tags` and `use_when`.
3. Skip a template when one of its `avoid_when` entries matches the user's situation.
4. Read the chosen template's `template.yaml` and `README.md` before you write anything.
5. If nothing fits, tell the user and write the code without a template. Do not stretch a template to a case it was not made for.

## Apply a template

- Take the files from `<path>/files/`. They work as they are with the default values.
- Change only the variables listed under `variables`. `where` names the file that sets each one, relative to `files/`.
- Keep every entry under `practices`. They are the reason the template exists.
- If the user's project forces you to break a practice, say so to the user explicitly: name the practice by its `id`, say what you did instead and why. Never drop a practice silently.
- If the project needs changes beyond the listed variables, keep them small and list them for the user.

## Versions

- Use the versions pinned in the template files and in `tools`. Do not invent versions.
- Do not replace a pinned version with `latest`, a range or a floating tag.
- If the project already pins a different version of a tool, keep the project's version and tell the user about the difference.

## Checks

- `checks` lists what CI verifies for the template. When the user's project can run them, copy the template's tests and lint configs along with its files.
- Do not remove or weaken a check to make something pass. Fix the cause, or tell the user why it fails.

## Changing this repository

- A template lives in `<category>/<template>/` with `template.yaml`, `files/`, `README.md` and, if needed, `tests/`. The metadata must match `schema/template.schema.json`.
- After any change to a `template.yaml`, run `python tools/catalog.py` and commit `catalog.json` and `CATALOG.md` with it. CI runs `python tools/catalog.py --check` and fails if they are out of date.
