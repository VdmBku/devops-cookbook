# devops-cookbook

Small, working examples of how I build delivery pipelines and infrastructure. Each one backs a line in the "Selected work" section of my [GitHub profile](https://github.com/VdmBku): the profile says what I did, the example shows how.

Everything here is written from scratch for this repository. None of it comes from client or employer code.

## How it's organized

Each example lives in its own folder. Its README covers the problem, the approach, how to run it and what CI checks. Every example has its own workflow, so a green badge means that example passed, not just the repository as a whole.

## Repository checks

[![checks](https://github.com/VdmBku/devops-cookbook/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/VdmBku/devops-cookbook/actions/workflows/checks.yml)

Every push runs the pre-commit hooks and a gitleaks scan of the full git history. To run the same hooks locally:

    pip install pre-commit
    pre-commit install

## License

[MIT](LICENSE)
