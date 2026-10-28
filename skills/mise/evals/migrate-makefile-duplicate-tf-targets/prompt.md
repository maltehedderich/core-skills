---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We're moving this repo from make to mise. Replace the Makefile with mise tasks. There are a bunch of near-duplicate terraform targets in there (tf-apply, terraform-apply, terraform-apply-development and so on), so clean those up properly. Update CI and the README too.

Input files: Makefile, README.md, pyproject.toml, .env.example, .github/workflows/ci.yml, .github/workflows/deploy.yml, infra/
