---
name: mise
description: "Set up, migrate, or maintain a project on the team's mise stack: mise tools and tasks under one shared task-naming convention, uv for Python, bun for JavaScript and TypeScript, Terraform in terraform/, and optional fnox secrets (Proton Pass locally, GitHub secrets in CI). Invoke it to replace a Makefile, justfile, or package scripts, add or rename tasks, add secrets or environments, or bootstrap a repository."
disable-model-invocation: true
---

# mise

Every project uses the same tools, and every task has the same name in every repository. mise installs the tools and runs the tasks. uv runs Python, bun runs JavaScript and TypeScript, and Terraform lives in `terraform/`. When tasks need secrets on a developer's machine, fnox reads them from Proton Pass. In CI, they come from the CI system's own secret store. Someone who knows one project can run `mise run setup`, `mise run check`, or `mise run tf:plan staging` in any other without reading its config.

The user invokes this skill explicitly. With a specific request, do that job. Without one, inspect the repository, report where it differs from the stack, and propose the changes before making them.

## The stack

| Concern | Tool | Where it lives |
| --- | --- | --- |
| Tool versions | mise | `[tools]` in `mise.toml`; exact versions in `mise.lock` |
| Tasks | mise | `[tasks]` in `mise.toml`; longer scripts in `mise-tasks/` |
| Non-secret environment | mise | `[env]` in `mise.toml` |
| Python | uv, with Python from mise | `pyproject.toml`, `uv.lock` |
| JavaScript and TypeScript | bun | `package.json`, `bun.lock` |
| Infrastructure | Terraform | `terraform/environments/<env>/`, `terraform/modules/` |
| Secrets, local (optional) | fnox, with Proton Pass (`pass-cli`) as the default backend | references in `fnox.toml`; values in one vault per environment |
| Secrets, CI | the CI system's secret store, such as GitHub environment secrets | `MISE_ENV=ci` loads `mise.ci.toml`, which turns the fnox wrapper off |

The environments are `development`, `staging`, and `production`. The same string is the task argument, the Terraform directory, the GitHub environment, and, with fnox, the profile and the vault suffix.

The stack replaces Make, just, npm/yarn/pnpm, pip/poetry, `.tool-versions`/`.nvmrc`/`.python-version`, and secrets in `.env` files. Keeping an old mechanism beside the new one leaves two answers to the same question, and they drift.

## References

| Job | Read |
| --- | --- |
| Name, add, or rename any task | [task-naming.md](references/task-naming.md), before writing the first task name |
| `mise.toml`: tools, lockfile, Python with uv, bun, `[env]`, task syntax, monorepos | [mise.md](references/mise.md) |
| Terraform layout, `tf:*` tasks, plan and apply | [terraform.md](references/terraform.md) |
| Secrets: when to add fnox, `fnox.toml`, Proton Pass or another backend, wrapping commands | [secrets.md](references/secrets.md) |
| GitHub Actions, `mise.ci.toml`, and secrets in CI | [ci.md](references/ci.md) |

The references were verified against mise 2026.10.21, fnox 1.43.0, and pass-cli 2.5.1. If a command behaves differently from what they say, check the current docs (Context7 `/jdx/mise` and `/jdx/fnox`) before working around it, and tell the user which reference is out of date.

## Rules

1. **mise tasks are the only interface.** CI, docs, Dockerfiles, git hooks, and people all call `mise run <task>`. When a workflow file or README repeats a task's commands, the copies drift from `mise.toml`.
2. **One canonical name per action.** Take every name from [task-naming.md](references/task-naming.md). The environment is an argument (`tf:apply production`), never part of the name, and tools never appear in names (`lint`, not `ruff`). Legacy names do not survive as aliases or wrapper targets. This is how `tf-apply`, `terraform-apply`, and `terraform-apply-development` become one `tf:apply <env>` in every repository.
3. **Secrets reach only the command that needs them.** Locally, a task wraps that one command in `fnox exec --only <keys>` through a `with_<scope>_secrets` var. In CI, `mise.ci.toml` empties the var, and the step's environment provides the same names from GitHub environment secrets. Never put a secret in `mise.toml`, `[env]`, a committed `.env`, a command line, or output, and never print a value to check it. mise exports `[env]` into every task and shell, so a secret there reaches every process.
4. **Add fnox only when needed.** A project whose tasks need no secrets has no `fnox.toml`, no `with_*` vars, and no `mise.ci.toml`. Proton Pass is the default backend. Use another fnox provider only when the project already has one or the user asks for it; only the provider configuration changes ([secrets.md](references/secrets.md#other-backends)).
5. **Versions live only in `mise.toml` and are locked in `mise.lock`.** Request major.minor and commit the lockfile, so laptops and CI install the same checksummed binaries.
6. **Shared environments are the user's call.** Never run `tf:apply`, `tf:destroy`, `deploy`, `docker:push`, or `db:migrate`/`db:seed` against a deployed environment unless the user explicitly asks for that run. Run `tf:plan` or `fnox check` against `staging` or `production` only when asked: both read real credentials, and the reads appear in the vault's access log.
7. **Stable features only.** Experimental mise features (`[secrets.fnox]`, task `secrets`, `[deps]`) would need `experimental = true` in every committed config. [mise.md](references/mise.md#deliberately-not-used) lists what is deliberately left out.

## Set up a project

1. **Inspect first.** Find the languages (`pyproject.toml`, `package.json`), Terraform files, existing task runners (Makefile, justfile, package scripts, `scripts/`), version files, `.env` files, CI workflows, and where secrets come from today.
2. **Write `mise.toml`** from the base configuration in [mise.md](references/mise.md#base-configuration). Include only the sections the project needs. Look up current versions with `mise latest <tool>` and write major.minor.
3. **Add tasks.** Define only the lifecycle verbs that apply. `check` depends on whichever of `lint`, `typecheck`, and `test` exist. With Terraform, copy the `tf:*` block from [terraform.md](references/terraform.md#tasks) and make root `lint` and `format` depend on `tf:lint` and `tf:format`.
4. **Lay out Terraform** as `terraform/environments/<env>/` plus `terraform/modules/` ([terraform.md](references/terraform.md#layout)).
5. **Add secrets, if any task needs them.** Write `fnox.toml` and the `with_<scope>_secrets` vars from [secrets.md](references/secrets.md), with vaults named `<project>-<env>` and each item named exactly like its variable. Add `mise.ci.toml` from [ci.md](references/ci.md#the-ci-config-environment). Without secrets, drop the `with_tf_secrets` prefix and run `terraform` directly.
6. **Update `.gitignore`** with `mise.local.toml`, `mise.*.local.toml`, `.venv/`, the Terraform patterns from [terraform.md](references/terraform.md#ignore-and-commit), and with fnox, `fnox.local.toml` and `.fnox.local.toml`. `mise.ci.toml` is committed.
7. **Add CI** from [ci.md](references/ci.md), with `MISE_ENV: ci` in every workflow and each secret mapped onto the steps that need it.
8. **Install and lock.** Run `mise trust`, `mise install`, and `mise lock`, then commit `mise.lock` along with `mise.toml`.

## Migrate a Makefile, justfile, or package scripts

1. **Inventory.** For every target, record its name, prerequisites, recipe, the variables it reads, and whether it builds a file. Then find every caller: CI workflows, Dockerfiles, READMEs and docs, scripts, git hooks, and other Makefiles (`git grep -nE '\bmake\b'`).
2. **Map to canonical names** with [task-naming.md](references/task-naming.md#renaming-legacy-targets). Collapse targets that differ only by environment or spelling into one task with an environment argument. If the members of a group differ in behavior, such as different flags, var files, or directories, find out which behavior is intended from the history and callers, then ask the user. Never pick one silently.
3. **Translate.**
   - Prerequisites become `depends`.
   - Make variables become `[vars]` or `usage` flags. An environment variable like `ENV ?= dev` becomes the `<env>` argument, required and without a default for deployed-only tasks.
   - Targets that build files keep their incremental behavior with `sources` and `outputs`.
   - Recipes longer than about five lines become file tasks in `mise-tasks/<scope>/<verb>`.
   - `include .env`, `export`ed secrets, and inline tokens move to fnox for local use and to CI environment secrets for CI.
   - Tool installs in recipes (`brew install`, `pip install`, `curl | sh`) become `[tools]` entries.
   - The `help` target is dropped, because `mise tasks ls` replaces it.
4. **Decide the leftovers with the user.** Name actions without a canonical verb using [When nothing fits](references/task-naming.md#when-nothing-fits). List targets that look dead (no callers, broken recipe) and let the user decide. Do not quietly drop or carry them over.
5. **Move Terraform to `terraform/`** when it lives elsewhere (`infra/`, `iac/`): use `git mv`, update every path, and rerun `tf:init`. If the environments are workspaces or tfvars files in one root module, keep that layout for now and point the `tf:*` tasks at it. Moving to one directory per environment moves state, so propose it as a separate change. The task names and arguments stay the same either way.
6. **Switch package managers only with agreement.** Moving npm, yarn, or pnpm to bun, or pip or poetry to uv, changes the lockfile and can change resolved versions, so it is a separate, agreed change. The task names do not change.
7. **Update every caller** to `mise run <task> [env]`, and switch CI to `jdx/mise-action` with `MISE_ENV: ci` ([ci.md](references/ci.md)).
8. **Delete the old runner.** Do not leave a Makefile that forwards to mise: it keeps the old names alive.

## Verify

Run these without secrets or side effects:

```sh
mise tasks validate               # every task definition is valid
mise tasks ls                     # names and descriptions follow the convention
mise run tf:plan --help           # the env argument and its choices
mise run -n tf:plan staging       # dry run: prints the commands, runs nothing
MISE_ENV=ci mise run -n tf:plan staging   # with fnox: the same commands without the wrapper
mise run check                    # lint, typecheck, and tests pass
```

- Search the repository for each legacy name from the mapping (and for `make `), so no caller still uses one.
- With fnox, compare the keys in each `with_*` var against `fnox.toml` and against the secrets mapped in the workflows, so no key is missing locally or in CI.
- If the user has a `pass-cli` session, `mise exec -- fnox check --all -P development` confirms that the development secrets resolve, without printing them.
- When a check cannot run, for example because tools are not installed or there is no Proton Pass session, say so in the report instead of skipping it silently.

## Report

- Files created, changed, and deleted.
- For a migration, a table of each old target and its new task, including the ones merged, renamed, or awaiting a decision.
- What was verified and what was not.
- Manual steps that only the user can do, with exact names: the Proton Pass vaults and the items in each, `pass-cli login`, the GitHub environments and the secrets in each, and `mise trust` on each machine.
- Open decisions, such as duplicate targets that behaved differently, or a proposed Terraform layout change.
