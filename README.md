# devops-cookbook

My library of ready-to-use DevOps templates, sorted by tool. Take a template, change the variables it lists, apply it.

Each template is a set of working files plus notes on the practices behind it: what was decided and why. That makes it a starting point for people, and a reference for AI coding assistants that should follow the same practices instead of guessing.

Everything here is written from scratch for this repository. None of it comes from client or employer code.

Templates are added one at a time. Each one has to pass its own checks in CI before it lands on `main`.

## Repository checks

[![checks](https://github.com/VdmBku/devops-cookbook/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/VdmBku/devops-cookbook/actions/workflows/checks.yml)

Every push runs the pre-commit hooks and a gitleaks scan of the full git history. To run the same hooks locally:

    pip install pre-commit
    pre-commit install

## License

[MIT No Attribution](LICENSE). Copy the templates into your own code without keeping a notice.
