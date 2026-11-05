---
name: mise
description: "Set up, migrate, or maintain a project on the team's mise stack: mise tools and tasks under one shared task-naming convention, deployment environments as mise config environments (mise.<env>.toml), uv for Python, bun for JavaScript and TypeScript, Terraform in terraform/, and optional fnox secrets (Proton Pass locally, environment variables in CI and on deployed hosts). Invoke it to replace a Makefile, justfile, or package scripts, add or rename tasks, add secrets or environments, or bootstrap a repository."
---

# mise

Every project uses the same tools, and every task has the same name in every repository. mise installs the tools, runs the tasks, and loads each deployment environment's configuration. uv runs Python, bun runs JavaScript and TypeScript, and Terraform lives in `terraform/`. When tasks need secrets on a developer's machine, fnox reads them from Proton Pass. In CI and on deployed hosts, they arrive as environment variables, or fnox reads them from a cloud secret manager with the machine's own identity. Someone who knows one project can run `mise run setup`, `mise run check`, or `mise -E staging run tf:apply` in any other without reading its config.

Use this skill for relevant tooling and task requests, or when the user invokes it explicitly. With a specific request, do that job. Without one, inspect the repository, report where it differs from the stack, and propose the changes before making them.

## The stack

| Concern | Tool | Where it lives |
| --- | --- | --- |
| Tool versions | mise | `[tools]` in `mise.toml`; exact versions in `mise.lock` |
| Tasks | mise | `[tasks]` in `mise.toml`; longer scripts in `mise-tasks/` |
| Non-secret environment | mise | `[env]` in `mise.toml` for every environment, `mise.<env>.toml` for one |
| Deployment environments | mise config environments | `mise.<env>.toml`, selected with `mise -E <env>` locally and `MISE_ENV` in CI |
| Python | uv, with Python from mise | `pyproject.toml`, `uv.lock` |
| JavaScript and TypeScript | bun | `package.json`, `bun.lock` |
| Infrastructure | Terraform | `terraform/environments/<env>/`, `terraform/modules/` |
| Secrets, local (optional) | fnox, with Proton Pass (`pass-cli`) as the default backend | references in `fnox.toml`; values in one vault per environment |
| Secrets, CI and deployed hosts | the platform's secret store, such as GitHub environment secrets | environment variables; `SECRETS_FROM_ENV=1` turns the fnox wrapper off. With AWS or GCP Secret Manager, fnox reads them with the machine's own identity instead. |

The environments are `development`, `staging`, and `production`. The same string is the mise config environment (`mise.<env>.toml`, `-E <env>`, `MISE_ENV`), the Terraform directory, the GitHub environment, and, with fnox, the profile and the vault suffix. Without an environment selected, tasks act on the local machine.

The stack replaces Make, just, npm/yarn/pnpm, pip/poetry, `.tool-versions`/`.nvmrc`/`.python-version`, per-environment `.env` files, and secrets in `.env` files. Keeping an old mechanism beside the new one leaves two answers to the same question, and they drift.

## References

| Job | Read |
| --- | --- |
| Name, add, or rename any task | [task-naming.md](references/task-naming.md), before writing the first task name |
| `mise.toml` and `mise.<env>.toml`: tools, lockfile, environments, Python with uv, bun, `[env]`, task syntax, monorepos | [mise.md](references/mise.md) |
| Terraform layout, `tf:*` tasks, plan and apply | [terraform.md](references/terraform.md) |
| Secrets: when to add fnox, `fnox.toml`, Proton Pass or another backend, wrapping commands | [secrets.md](references/secrets.md) |
| GitHub Actions, environments in CI, and secrets in CI | [ci.md](references/ci.md) |

The references were verified against mise 2026.11.2, fnox 1.47.0, Terraform 1.17.1, and pass-cli 2.5.1. If a command behaves differently from what they say, check the current docs (Context7 `/jdx/mise` and `/jdx/fnox`) before working around it, and tell the user which reference is out of date.

## Rules

1. **mise tasks are the only interface.** CI, docs, Dockerfiles, git hooks, and people all call `mise run <task>`. When a workflow file or README repeats a task's commands, the copies drift from `mise.toml`.
2. **One canonical name per action.** Take every name from [task-naming.md](references/task-naming.md). The environment is never part of the name (`mise -E production run tf:apply`), and tools never appear in names (`lint`, not `ruff`). Legacy names do not survive as aliases or wrapper targets. This is how `tf-apply`, `terraform-apply`, and `terraform-apply-development` become one `tf:apply` in every repository.
3. **Deployment environments are mise config environments.** Each one has a committed `mise.<env>.toml` that sets `DEPLOY_ENV` and the environment's other non-secret settings. Select it for each command with `mise -E <env>`, and in CI with `MISE_ENV` on the job. `mise.toml` unsets `DEPLOY_ENV`, and tasks that act on a deployed environment require it, so a missing or misspelled environment fails instead of reaching some environment. Never select a deployed environment persistently: no exported `MISE_ENV` in a shell profile and no committed `.miserc.toml` ([mise.md](references/mise.md#environments)).
4. **Secrets reach only the command that needs them.** A task wraps that one command in `fnox exec --only <keys>` through a `with_<scope>_secrets` var, and the environment file's `FNOX_PROFILE` picks the vault. Where the platform provides secrets as environment variables (CI, deployed hosts), `SECRETS_FROM_ENV=1` makes the var render empty, and the command reads the same names directly. Never put a secret in `mise.toml`, `mise.<env>.toml`, `[env]`, a committed `.env`, a command line, or output, and never print a value to check it. mise exports `[env]` into every task and shell, so a secret there reaches every process.
5. **Add fnox only when needed.** A project whose tasks need no secrets has no `fnox.toml`, no `with_*` vars, and no `FNOX_PROFILE`. Proton Pass is the default backend. Use another fnox provider only when the project already has one or the user asks for it; only the provider configuration changes ([secrets.md](references/secrets.md#other-backends)). When the secrets already live in AWS Secrets Manager or GCP Secret Manager, CI and deployed hosts read them through fnox too, with their own identity (OIDC in CI), and nobody sets `SECRETS_FROM_ENV` ([secrets.md](references/secrets.md#cloud-secret-managers), [ci.md](references/ci.md#secrets-from-a-cloud-secret-manager)).
6. **Versions live only in `mise.toml` and are locked in `mise.lock`.** Request major.minor and commit the lockfile, so laptops and CI install the same checksummed binaries. Environment files never declare tools.
7. **Shared environments are the user's call.** Never run `tf:apply`, `tf:destroy`, `deploy`, `docker:push`, or `db:migrate`/`db:seed` with a deployed environment selected unless the user explicitly asks for that run. Run `tf:plan` or `fnox check` against `staging` or `production` only when asked: both read real credentials, and the reads appear in the vault's access log. Pass `-E` per command; never export `MISE_ENV` in an agent's shell.
8. **Stable features only.** Experimental mise features (`[secrets.fnox]`, task `secrets`, `[deps]`) would need `experimental = true` in every committed config. [mise.md](references/mise.md#deliberately-not-used) lists what is deliberately left out.

## Set up a project

1. **Inspect first.** Find the languages (`pyproject.toml`, `package.json`), Terraform files, existing task runners (Makefile, justfile, package scripts, `scripts/`), version files, `.env` files, CI workflows, the deployment environments, and where secrets come from today.
2. **Write `mise.toml`** from the base configuration in [mise.md](references/mise.md#base-configuration). Include only the sections the project needs. Look up current versions with `mise latest <tool>` and write major.minor.
3. **Add one `mise.<env>.toml` per deployment environment** from [mise.md](references/mise.md#environments), with `DEPLOY_ENV` and only the non-secret settings that tasks, scripts, or tools need.
4. **Add tasks.** Define only the lifecycle verbs that apply. `check` depends on whichever of `lint`, `typecheck`, and `test` exist. With Terraform, copy the `tf:*` block from [terraform.md](references/terraform.md#tasks) and make root `lint` and `format` depend on `tf:lint` and `tf:format`.
5. **Lay out Terraform** as `terraform/environments/<env>/` plus `terraform/modules/` ([terraform.md](references/terraform.md#layout)).
6. **Add secrets, if any task needs them.** Write `fnox.toml` and the `with_<scope>_secrets` vars from [secrets.md](references/secrets.md), with vaults named `<project>-<env>` and each item named exactly like its variable, and add `FNOX_PROFILE` to each environment file. Without secrets, drop the `with_tf_secrets` prefix and run `terraform` directly.
7. **Update `.gitignore`** with `mise.local.toml`, `mise.*.local.toml`, `.venv/`, the Terraform patterns from [terraform.md](references/terraform.md#ignore-and-commit), and with fnox, `fnox.local.toml` and `.fnox.local.toml`. The `mise.<env>.toml` files are committed.
8. **Add CI** from [ci.md](references/ci.md): jobs that target an environment set `MISE_ENV` to it. With fnox and Proton Pass, they also set `SECRETS_FROM_ENV: "1"` and map each secret onto the steps that need it. With a cloud secret manager, they get an OIDC identity instead.
9. **Install and lock.** Run `mise trust`, `mise install`, and `mise lock`, then commit `mise.lock` along with `mise.toml`.

## Migrate a Makefile, justfile, or package scripts

1. **Inventory.** For every target, record its name, prerequisites, recipe, the variables it reads, and whether it builds a file. Then find every caller: CI workflows, Dockerfiles, READMEs and docs, scripts, git hooks, and other Makefiles (`git grep -nE '\bmake\b'`).
2. **Map to canonical names** with [task-naming.md](references/task-naming.md#renaming-legacy-targets). Collapse targets that differ only by environment or spelling into one task, and a plan target and an apply target into `tf:plan` and a `tf:apply` that plans itself. If the members of a group differ in behavior, such as different flags, var files, or directories, find out which behavior is intended from the history and callers, then ask the user. Never pick one silently.
3. **Translate.**
   - Prerequisites become `depends`.
   - Make variables become `[vars]` or `usage` flags. An environment selector like `ENV ?= dev` becomes the config environment: `make tf-apply ENV=prod` becomes `mise -E production run tf:apply`. Tasks for deployed environments extend the `deployed` template, so they have no default environment.
   - Non-secret values that differ per environment (`.env.staging`, per-environment Make variables, `case $ENV` blocks in scripts) move to `[env]` in `mise.<env>.toml`.
   - Existing config environments with short names (`mise.prod.toml`) are renamed to the full names. A `mise.development.toml` or `mise.dev.toml` that configures the laptop moves into `mise.toml` or `mise.local.toml`, because `development` is the deployed environment.
   - Targets that build files keep their incremental behavior with `sources` and `outputs`.
   - Recipes longer than about five lines become file tasks in `mise-tasks/<scope>/<verb>`.
   - `include .env`, `export`ed secrets, and inline tokens move to fnox for local use and to the platform's secret store for CI.
   - Tool installs in recipes (`brew install`, `pip install`, `curl | sh`) become `[tools]` entries.
   - The `help` target is dropped, because `mise tasks ls` replaces it.
4. **Decide the leftovers with the user.** Name actions without a canonical verb using [When nothing fits](references/task-naming.md#when-nothing-fits). List targets that look dead (no callers, broken recipe) and let the user decide. Do not quietly drop or carry them over.
5. **Move Terraform to `terraform/`** when it lives elsewhere (`infra/`, `iac/`): use `git mv`, rename environment directories to the full names, update every path, and rerun `tf:init` for each environment. If the environments are workspaces or tfvars files in one root module, keep that layout for now and point the `tf:*` tasks at it. Moving to one directory per environment moves state, so propose it as a separate change. The task names and environment files stay the same either way.
6. **Switch package managers only with agreement.** Moving npm, yarn, or pnpm to bun, or pip or poetry to uv, changes the lockfile and can change resolved versions, so it is a separate, agreed change. The task names do not change.
7. **Update every caller** to `mise run <task>` or `mise -E <env> run <task>`, and switch CI to `jdx/mise-action` with `MISE_ENV` on each job that targets an environment ([ci.md](references/ci.md)).
8. **Delete the old runner.** Do not leave a Makefile that forwards to mise: it keeps the old names alive.

## Verify

Run these without secrets or side effects:

```sh
mise tasks validate                      # every task definition is valid
mise tasks ls                            # names and descriptions follow the convention
mise run -n tf:plan                      # fails: no environment selected
mise -E staging config ls                # mise.toml and mise.staging.toml load
mise -E staging run -n --yes tf:apply    # dry run: prints init, plan, and apply; runs nothing
SECRETS_FROM_ENV=1 mise -E staging run -n --yes tf:apply   # with fnox: the same commands without the wrapper
mise run check                           # lint, typecheck, and tests pass
```

- Search the repository for each legacy name from the mapping (and for `make `), so no caller still uses one.
- Check that every environment in the `deployed` template's help text has a `mise.<env>.toml`, a Terraform directory, and, with fnox, a profile.
- With fnox, compare the keys in each `with_*` var against `fnox.toml` and against the secrets mapped in the workflows, so no key is missing locally or in CI.
- If the user has a `pass-cli` session, `mise exec -- fnox check --all -P development` confirms that the development secrets resolve, without printing them.
- When a check cannot run, for example because tools are not installed or there is no Proton Pass session, say so in the report instead of skipping it silently.

## Report

- Files created, changed, and deleted.
- For a migration, a table of each old target and its new command (`mise -E <env> run <task>` where an environment applies), including the ones merged, renamed, or awaiting a decision.
- What was verified and what was not.
- Manual steps that only the user can do, with exact names: the Proton Pass vaults and the items in each (or the cloud secrets and the OIDC roles or service accounts), `pass-cli login`, the GitHub environments and the secrets or variables in each, `SECRETS_FROM_ENV=1` on any deployed host that runs tasks with secrets from its environment, and `mise trust` on each machine.
- Open decisions, such as duplicate targets that behaved differently, or a proposed Terraform layout change.
