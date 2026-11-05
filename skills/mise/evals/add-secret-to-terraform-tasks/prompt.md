---
tags: [skill-creator]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

We're adding Cloudflare DNS records to our Terraform. Wire up a CLOUDFLARE_API_TOKEN so tf:plan and tf:apply get it, both locally and in CI. You don't need to write the DNS resources yet.

Input files: mise.toml, mise.development.toml, mise.staging.toml, mise.production.toml, fnox.toml, .github/workflows/terraform.yml, terraform/environments/
