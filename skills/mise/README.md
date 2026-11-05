# mise

Set up, migrate, and maintain projects on one shared tooling stack: mise for tool versions, tasks, and deployment environments, uv for Python, bun for JavaScript and TypeScript, and Terraform in `terraform/`. When tasks need secrets on a developer's machine, fnox reads them from Proton Pass. In CI, they come from GitHub environment secrets, or from AWS or GCP Secret Manager through fnox.

The core of the skill is a task-naming convention. Every repository uses the same names for the same actions: `setup`, `check`, `test:unit`, `tf:apply`, `deploy`. The environment is a mise config environment (`mise.staging.toml`) selected with `-E`, never part of the name, so `tf-apply`, `terraform-apply`, and `terraform-apply-development` all become `mise -E <env> run tf:apply`.

## Install

From the repository root:

```sh
./coreskills install --tool codex --skills mise
```

Replace `codex` with `claude`, `copilot`, or `gemini` for another tool.

## Use

The assistant can select this skill automatically for relevant tooling and task requests. You can also invoke it with `$mise` in Codex or `/mise` in Claude Code. Work from the project's repository so the assistant can read its Makefile, CI workflows, and Terraform layout.

```text
Use $mise to replace our Makefile with mise tasks. Merge duplicate targets into the canonical names and update CI.
```

```text
Use $mise to set up this new Python API with Terraform for development, staging, and production. Secrets come from Proton Pass locally and from GitHub secrets in CI.
```

```text
Use $mise to add a CLOUDFLARE_API_TOKEN secret to our Terraform tasks.
```

## What the skill enforces

- One canonical name per action, from a fixed vocabulary.
- Deployment environments as mise config environments: `mise.development.toml`, `mise.staging.toml`, and `mise.production.toml` hold each environment's non-secret settings, and `mise -E <env>` (or `MISE_ENV` in CI) selects one. Tasks for deployed environments fail when none is selected; without one, tasks act on the local machine.
- Tool versions only in `mise.toml`, locked in `mise.lock`.
- Python through uv and JavaScript through bun, with mise providing the runtimes.
- Terraform as one directory per environment. `tf:apply` plans, prints the plan, asks, and applies exactly that plan in one command.
- Optional secrets through fnox: each command resolves only the keys it needs, from one Proton Pass vault per environment. Other fnox backends work when a project specifies one.
- CI runs the same tasks with the same environment files. `SECRETS_FROM_ENV=1` turns the fnox wrapper off so GitHub environment secrets supply the same variables, or, with a cloud secret manager, CI reads through fnox with an OIDC identity.
- Agents never apply, destroy, or deploy against a shared environment unless the user explicitly asks.

## Instructions and references

| File | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Stack, rules, setup and migration workflows, verification, and report. |
| [task-naming.md](references/task-naming.md) | The task-naming convention, vocabulary, and legacy-name mapping. |
| [mise.md](references/mise.md) | Tools, lockfile, environments, Python with uv, bun, environment variables, task syntax, and monorepos. |
| [terraform.md](references/terraform.md) | Layout, `tf:*` tasks, plan and apply, and TFLint. |
| [secrets.md](references/secrets.md) | fnox with Proton Pass, a cloud secret manager, or another backend, and secrets in tasks. |
| [ci.md](references/ci.md) | GitHub Actions workflows, environments in CI, and secrets in CI. |
