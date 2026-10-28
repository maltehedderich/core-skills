# CI with mise

CI runs the same tasks as a laptop: `mise run setup`, `mise run check`, `mise run tf:plan staging`. Do not repeat tool installs or task commands in workflow YAML, because the copies drift from `mise.toml`. The examples use GitHub Actions. Other CI systems need the same things: install mise, set `MISE_ENV=ci`, provide secrets as environment variables, and run tasks.

## Contents

- [The ci config environment](#the-ci-config-environment)
- [Check workflow](#check-workflow)
- [Terraform and deploy workflow](#terraform-and-deploy-workflow)
- [Secrets in CI](#secrets-in-ci)
- [Pull requests from forks](#pull-requests-from-forks)
- [Monorepos](#monorepos)

## The ci config environment

Every workflow sets `MISE_ENV: ci`, so mise loads `mise.ci.toml` on top of `mise.toml`. A project with fnox needs that file, because CI gets secrets from its own secret store instead of Proton Pass:

```toml
# mise.ci.toml, loaded when MISE_ENV=ci
# CI sets secrets from its own secret store, so commands run without fnox.
[vars]
with_tf_secrets = ""

[settings]
disable_tools = ["fnox", "aqua:protonpass/pass-cli"]
```

- Empty every `with_<scope>_secrets` var that `mise.toml` defines. A var left out of this file makes the task call fnox in CI, which then fails without a vault login.
- `disable_tools` skips installing fnox and `pass-cli` on runners. With `MISE_ENV=ci`, `mise install --locked` still uses the one `mise.lock`.
- Keep the file to CI differences. Tools, tasks, and everything else stay in `mise.toml`.
- A project without fnox needs no `mise.ci.toml`. Setting `MISE_ENV: ci` anyway is harmless and keeps workflows uniform.

## Check workflow

```yaml
name: check
on:
  pull_request:
  push:
    branches: [main]

env:
  MISE_ENV: ci

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: jdx/mise-action@v5   # installs the tools; uses --locked when mise.lock exists
      - run: mise run setup
      - run: mise run check
```

- `check` needs no secrets: unit tests, lint, typecheck, and `tf:lint` all run without them. A test suite that needs a secret belongs in a separate job with an environment.
- `mise run setup` and `mise run check` are separate steps. `mise run setup ::: check` would run them in parallel.
- `mise generate github-action --write --task=check` writes a starting workflow. Review its triggers, action versions, and `MISE_ENV` before committing it.

## Terraform and deploy workflow

```yaml
name: terraform
on:
  workflow_dispatch:
    inputs:
      env:
        description: Target environment
        type: choice
        options: [development, staging, production]

env:
  MISE_ENV: ci

jobs:
  apply:
    runs-on: ubuntu-latest
    environment: ${{ inputs.env }}              # GitHub environment: protection rules and its own secrets
    concurrency: terraform-${{ inputs.env }}    # never two applies against one state
    env:
      TF_ENV: ${{ inputs.env }}
    steps:
      - uses: actions/checkout@v7
      - uses: jdx/mise-action@v5
      - run: mise run tf:plan "$TF_ENV"
        env:
          HCLOUD_TOKEN: ${{ secrets.HCLOUD_TOKEN }}
          TF_VAR_db_password: ${{ secrets.TF_VAR_db_password }}
      - run: mise run tf:apply "$TF_ENV"
        env:
          HCLOUD_TOKEN: ${{ secrets.HCLOUD_TOKEN }}
          TF_VAR_db_password: ${{ secrets.TF_VAR_db_password }}
          MISE_YES: "1"                         # accept the task's confirm prompt
```

- Create one GitHub environment per stack environment, with the same names (`development`, `staging`, `production`). Give `production` required reviewers.
- Plan and apply run in the same job, so the plan file, which contains secrets in plain text, is never uploaded.
- Only the apply step sets `MISE_YES`. Every other `confirm` in the run still fails without a terminal.
- `deploy <env>` jobs follow the same shape: secrets on the step, then `mise run deploy "$TF_ENV"` with `MISE_YES: "1"`.

## Secrets in CI

- Store each secret as a **GitHub environment secret** with the same name as its variable. Each environment holds its own values, so a job for `development` cannot read production values, and `production`'s protection rules gate every job that can.
- Map secrets onto the **steps** that run tasks needing them, as above, not onto the whole job. Then checkout and other actions never see them.
- The names to map are the keys in the `with_<scope>_secrets` vars. When a key is added there, add it to every environment and to the workflow.
- A secret missing from an environment arrives as an empty string, not an error. Terraform input variables reject empty values with a `validation` block (see [terraform.md](terraform.md#secrets)), and provider tokens fail at authentication.
- GitHub masks the values it injects in logs. GitHub shows secret names in upper case; the variable name in the workflow's `env` keeps its exact case (`TF_VAR_db_password`).
- CI never logs in to Proton Pass and has no Proton Pass token.

## Pull requests from forks

Fork pull requests receive no repository or environment secrets. That is fine, because the check workflow needs none. Never combine `pull_request_target` with a checkout of the fork's code in a job that holds secrets: the fork's code could read all of them.

## Monorepos

```yaml
      - run: mise run '//...:setup'
      - run: mise run '//...:check'
```

Keep `working_directory` unset so mise sees the monorepo root. `tf:*` tasks and their `mise.ci.toml` stay at the root, so the Terraform workflow does not change. A project that defines its own `with_*` vars gets a `mise.ci.toml` beside its `mise.toml`, because mise loads environment files per directory.
