# mise

Set up, migrate, and maintain projects on one shared tooling stack: mise for tool versions and tasks, uv for Python, bun for JavaScript and TypeScript, and Terraform in `terraform/`. When tasks need secrets on a developer's machine, fnox reads them from Proton Pass. In CI, they come from GitHub environment secrets.

The core of the skill is a task-naming convention. Every repository uses the same names for the same actions: `setup`, `check`, `test:unit`, `tf:plan <env>`, `deploy <env>`. The environment is an argument, never part of the name, so `tf-apply`, `terraform-apply`, and `terraform-apply-development` all become `mise run tf:apply <env>`.

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

- One canonical name per action, from a fixed vocabulary, with the environment as a validated argument (`development`, `staging`, `production`).
- Tool versions only in `mise.toml`, locked in `mise.lock`.
- Python through uv and JavaScript through bun, with mise providing the runtimes.
- Terraform as one directory per environment, with a saved plan that `tf:apply` applies after confirmation.
- Optional secrets through fnox: each command resolves only the keys it needs, from one Proton Pass vault per environment. Other fnox backends work when a project specifies one.
- CI runs the same tasks with `MISE_ENV=ci`, which turns the fnox wrapper off so GitHub environment secrets supply the same variables.
- Agents never apply, destroy, or deploy against a shared environment unless the user explicitly asks.

## Instructions and references

| File | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Stack, rules, setup and migration workflows, verification, and report. |
| [task-naming.md](references/task-naming.md) | The task-naming convention, vocabulary, and legacy-name mapping. |
| [mise.md](references/mise.md) | Tools, lockfile, Python with uv, bun, environment variables, task syntax, and monorepos. |
| [terraform.md](references/terraform.md) | Layout, `tf:*` tasks, plan and apply, and TFLint. |
| [secrets.md](references/secrets.md) | fnox with Proton Pass or another backend, and secrets in tasks. |
| [ci.md](references/ci.md) | GitHub Actions workflows, `mise.ci.toml`, and secrets in CI. |
