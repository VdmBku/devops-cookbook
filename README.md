# devops-cookbook

My library of ready-to-use DevOps templates, sorted by tool. Take a template, change the variables it lists, apply it.

Each template is a set of working files plus notes on the practices behind it: what was decided and why. That makes it a starting point for people, and a reference for AI coding assistants that should follow the same practices instead of guessing.

Everything here is written from scratch for this repository. None of it comes from client or employer code.

Templates are added one at a time. Each one has to pass its own checks in CI before it lands on `main`.

## How to use

[CATALOG.md](CATALOG.md) lists every template by category.

Each template folder has the same layout. `files/` holds the files themselves, and they work as they are with the default values. `template.yaml` lists the variables you can change, the practices the template follows and why, the pinned tool versions and what CI checks. `README.md` says the same in prose and explains how to apply the template.

To use a template, copy its `files/` into your project and change the variables it lists. Keep the practices unless you have a good reason to drop one. Each of them says why it is there.

If you work with an AI coding assistant, point it at [AGENTS.md](AGENTS.md). It tells the assistant how to find a template through [catalog.json](catalog.json) and apply it without dropping the practices.

## Repository checks

[![checks](https://github.com/VdmBku/devops-cookbook/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/VdmBku/devops-cookbook/actions/workflows/checks.yml) [![catalog](https://github.com/VdmBku/devops-cookbook/actions/workflows/catalog.yml/badge.svg?branch=main)](https://github.com/VdmBku/devops-cookbook/actions/workflows/catalog.yml)

Every push runs the pre-commit hooks and a gitleaks scan of the full git history. To run the same hooks locally:

    pip install pre-commit
    pre-commit install

Every push also validates each `template.yaml` against [the schema](schema/template.schema.json) and checks that the catalog files are current. After changing a template, rebuild them:

    pip install -r requirements-dev.txt
    python tools/catalog.py

## License

[MIT No Attribution](LICENSE). Copy the templates into your own code without keeping a notice.
