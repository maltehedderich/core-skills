---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Set this new repo up with our standard tooling. It's a FastAPI backend plus a React admin UI in web/, and it deploys to Hetzner with Terraform (development, staging and production). Terraform needs HCLOUD_TOKEN and a database password. Add the CI workflows as well.

Input files: pyproject.toml, src/shop_api/main.py, web/package.json, web/src/App.tsx, README.md
