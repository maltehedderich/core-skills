# Task naming convention

One action has one name in every repository. Someone who has run `mise run check` or `mise -E staging run tf:plan` in one project can run the same command in any other without opening its config, and CI templates, docs, and habits carry over. Every rule below serves that goal. Drift usually starts with a reasonable-looking local variant: `tf-apply` in one Makefile, `terraform-apply` in the next, `terraform-apply-development` in a third.

## Contents

- [Grammar](#grammar)
- [Vocabulary](#vocabulary)
- [Rules](#rules)
- [Environments](#environments)
- [Flags or variants](#flags-or-variants)
- [Monorepos](#monorepos)
- [Renaming legacy targets](#renaming-legacy-targets)
- [When nothing fits](#when-nothing-fits)

## Grammar

```text
mise [-E <env>] run [<scope>:]<verb>[:<variant>] [--flags]
```

- **verb**: from the vocabulary below. It names the action, never the tool (`lint`, not `ruff`).
- **scope** (optional): a domain with its own verbs (`tf`, `db`, `docker`), or a component in a single-config repository with several components (`api`, `web`).
- **variant** (optional): a named subset of the verb's work (`test:unit`, `test:e2e`).
- **env**: the mise config environment, selected with `-E <env>` before `run`, never part of the name. See [Environments](#environments).
- Lowercase only. `:` separates parts; a multi-word part uses `-` (`db:reset`, `test:e2e`). Underscores and other separators are not used.

In TOML, quote any name that contains `:`: `[tasks."tf:plan"]`. File tasks get their name from their path: `mise-tasks/tf/plan` is `tf:plan`.

## Vocabulary

### Lifecycle verbs

These are top-level tasks. A project defines only the ones it needs.

| Task | What it does | Replaces |
| --- | --- | --- |
| `setup` | Install project dependencies from the lockfiles (`uv sync --locked`, `bun install --frozen-lockfile`). Safe to rerun. mise installs the tools themselves before any task runs. | `install`, `bootstrap`, `init`, `deps`, `prepare`, `venv` |
| `dev` | Run the application locally with reload. | `start`, `serve`, `run`, `watch`, `local`, `up` |
| `build` | Produce build artifacts. | `compile`, `bundle`, `package`, `dist` |
| `test` | Run the full test suite. | `tests`, `spec`, `pytest`, `unittest` |
| `test:<variant>` | Run a subset: `test:unit`, `test:integration`, `test:e2e`. | `unit`, `test-unit`, `e2e`, `integration-test` |
| `lint` | Read-only static checks, including the formatting check. Never modifies files. | `check-format`, `fmt-check`, `vet`, `style`, `ruff`, `eslint` |
| `format` | Rewrite files: formatter plus safe lint autofixes. | `fmt`, `prettier`, `black`, `fix`, `lint-fix`, `autoformat` |
| `typecheck` | Static type checking. | `types`, `type-check`, `tsc`, `mypy`, `pyright` |
| `check` | Everything CI gates on. Depends on `lint`, `typecheck`, and `test`, whichever exist. | `ci`, `verify`, `validate`, `all`, `precommit`, `pre-commit` |
| `clean` | Delete generated files that `setup` or `build` can recreate. Never deletes state, data, or secrets. | `clobber`, `distclean`, `purge` |
| `deploy` | Ship the application to the selected environment. | `release`, `ship`, `push`, `deploy-prod`, `deploy-staging` |
| `publish` | Publish a package to a registry (PyPI, npm). | `release`, `upload` |

### Terraform: `tf:`

The scope is always `tf`, never `terraform`, `infra`, or `iac`. These tasks live in the repository-root `mise.toml`. See [terraform.md](terraform.md) for the definitions. Every `tf:*` task except `tf:lint` and `tf:format` acts on the environment selected with `-E` and fails without one.

| Task | What it does |
| --- | --- |
| `tf:init` | `terraform init` in `terraform/environments/<env>`. |
| `tf:plan` | Init, then plan and save the plan to `tfplan`. |
| `tf:apply` | Plan, print the plan, ask for confirmation, and apply exactly that plan. Needs no separate `tf:plan`. |
| `tf:destroy` | Destroy the environment's resources. Terraform asks for confirmation. |
| `tf:output` | Print the environment's outputs. |
| `tf:lint` | `terraform fmt -check` and `terraform validate` for every environment. Needs no secrets. |
| `tf:format` | `terraform fmt -recursive terraform`. |

`tf:lint` and `tf:format` are the Terraform halves of `lint` and `format`. When a project has Terraform, root `lint` depends on `tf:lint` and root `format` on `tf:format`.

### Database: `db:`

| Task | What it does |
| --- | --- |
| `db:migrate` | Apply pending migrations: locally, or with `-E <env>` to that environment. |
| `db:seed` | Load seed data: locally, or with `-E <env>` to that environment. |
| `db:reset` | Drop and recreate the local database. Local only: the task exits with an error when `DEPLOY_ENV` is set. |
| `db:start`, `db:stop` | Start or stop the local database service. |

### Containers: `docker:`

| Task | What it does |
| --- | --- |
| `docker:build` | Build the image. |
| `docker:push` | Push the image for the selected environment. |

## Rules

1. **Look up the name before writing a task.** If a verb above fits, use it exactly. The "Replaces" column lists names that must not appear.
2. **No environment in the name.** `mise -E production run tf:apply`, not `tf:apply-production` or `terraform-apply-prod`. See [Environments](#environments).
3. **No tool in the name** unless the tool is the scope. `test` runs pytest or `bun test`; `format` runs ruff or Biome. Projects can switch tools without renaming tasks.
4. **One name per action, no aliases.** Legacy spellings do not survive as `alias` entries, because aliases keep the old vocabulary alive. Personal shorthands belong in shell aliases (`alias mr='mise run'`).
5. **Aggregates list their parts explicitly.** `check` uses `depends = ["lint", "typecheck", "test"]`, not a wildcard, so the gate is readable and a missing task fails loudly.
6. **Every task has a `description`.** It appears in `mise tasks ls`, `--help`, and completions. Write it as an imperative sentence: "Run the test suite".
7. **Helpers follow the grammar and set `hide = true`.** A task that exists only as a dependency is hidden, not prefixed with `_`.
8. **Changes to a deployed environment ask first.** `tf:apply` and `deploy` use `confirm` (see [mise.md](mise.md#confirmation)), and `tf:destroy` leaves the prompt to Terraform.
9. **Tasks do what their name says everywhere.** `lint` never writes files; `test` never deploys; `setup` never touches deployed environments. A task that needs a side effect gets its own name.
10. **Omit tasks that do not apply.** A project without types has no `typecheck`, and `check` does not depend on it. Never add a placeholder task that does nothing.

## Environments

The environments are `development`, `staging`, and `production`. Each one is a mise config environment with a `mise.<env>.toml` (see [mise.md](mise.md#environments)). The same spelling is used for the config file and `-E`, the Terraform directory, the GitHub environment, and, with fnox, the profile and the vault suffix. Never abbreviate them (`dev`, `stg`, `prod`): one spelling means one string to search for, and `mise -E prod` loads no file and fails.

- Tasks that act only on deployed environments extend the `deployed` template, which requires `DEPLOY_ENV`: `tf:*` (except `tf:lint` and `tf:format`), `deploy`, `docker:push`. Without `-E` they fail instead of reaching some environment, because nothing but an environment file sets `DEPLOY_ENV`.
- Tasks that also run against the local machine do not extend the template. They check `DEPLOY_ENV` and act locally when it is empty: `db:migrate`, `db:seed`. They never default to a deployed environment.
- `development` is the deployed development environment, not the laptop. The laptop is what you get without `-E`.
- Every task has one definition for all environments. Environment files change settings (`[env]`), never tasks or tools.

## Flags or variants

A different **subset** of the work is a variant: `test:unit`, `test:e2e`. A different **mode** of the same work is a flag on the same task: `test --watch`, `build --release`, `dev --port 4000`. Declare flags in the task's `usage` spec so they appear in `--help`. The test is simple: if the task would otherwise copy another task's command with one option changed, it is a flag.

## Monorepos

In mise monorepo mode the project path is the scope: `//services/api:test`, `//web:lint`. Each project uses the bare canonical names in its own `mise.toml`. Do not prefix them again (`api:test` inside `services/api`).

- Run a verb across all projects with `mise run '//...:check'`. Do not define a root `check` that calls the same pattern, because `//...` includes the root and the task would match itself.
- `tf:*` tasks and the environment files stay in the repository root, so `mise -E staging run tf:plan` is the same command in single-project repositories and monorepos.
- In a single-config repository with separately built components, scope by component (`api:test`, `web:build`) and let the lifecycle task depend on them: `test` depends on `["api:test", "web:test"]`.

## Renaming legacy targets

Typical mappings when migrating from Make, just, or package scripts:

| Legacy names | Canonical |
| --- | --- |
| `tf-apply`, `terraform-apply`, `terraform-apply-development`, `apply-dev` | `tf:apply`, for example `mise -E development run tf:apply` |
| `tf-plan-prod`, `plan-production`, `terraform-plan` | `tf:plan`, for example `mise -E production run tf:plan` |
| A plan target followed by an apply target (`make plan && make apply`) | `tf:apply`, which plans and asks itself |
| `tf-fmt`, `terraform-fmt` | `tf:format` |
| `tf-validate`, `terraform-validate`, `tf-check` | `tf:lint` |
| `install`, `deps`, `bootstrap`, `init` | `setup` |
| `run`, `start`, `serve`, `up` | `dev` |
| `fmt`, `black`, `prettier`, `lint-fix` | `format` |
| `ci`, `all`, `verify`, `pre-commit` | `check` |
| `test-unit`, `unit`, `tests-unit` | `test:unit` |
| `test-watch`, `watch-test` | `test --watch` (a flag, not a task) |
| `docker-build`, `build-image`, `image` | `docker:build` |
| `migrate`, `db-migrate`, `migrate-prod` | `db:migrate`, with `-E production` for `migrate-prod` |
| `deploy-staging`, `deploy-prod`, `release-production` | `deploy`, for example `mise -E staging run deploy` |
| `ENV=prod make <target>`, `make <target> ENV=prod` | `mise -E production run <task>` |

When two legacy targets with the same canonical name do different things, find out which behavior is intended before merging them. Never pick one silently.

## When nothing fits

Choose a plain imperative verb, check that it is not a synonym of an existing verb, and use the grammar (`docs:build`, `api:generate`). If the action is likely to recur in other projects, tell the user that the shared convention should gain the verb, so the next project uses the same word instead of inventing its own.
