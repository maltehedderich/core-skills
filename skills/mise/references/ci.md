# CI with mise

CI runs the same tasks as a laptop: `mise run setup`, `mise run check`, and, with the environment selected through `MISE_ENV`, `mise run tf:apply`. Do not repeat tool installs or task commands in workflow YAML, because the copies drift from `mise.toml`. The examples use GitHub Actions. Other CI systems need the same things: install mise, set `MISE_ENV` on jobs that target an environment, provide secrets as environment variables with `SECRETS_FROM_ENV=1` (or an identity for a cloud secret manager), and run tasks.

## Contents

- [Environments in CI](#environments-in-ci)
- [Check workflow](#check-workflow)
- [Terraform and deploy workflow](#terraform-and-deploy-workflow)
- [Secrets in CI](#secrets-in-ci)
- [Secrets from a cloud secret manager](#secrets-from-a-cloud-secret-manager)
- [Pull requests from forks](#pull-requests-from-forks)
- [Monorepos](#monorepos)

## Environments in CI

CI uses the same environment files as a laptop. A job that targets an environment sets `MISE_ENV` to its name, which loads `mise.<env>.toml` exactly as `mise -E <env>` does locally, so the job runs with that environment's settings. Jobs that target no environment, like `check`, set nothing.

- Set `MISE_ENV` on the job rather than `-E` on each step, so every mise command in the job sees the same environment. Take it from the same workflow input that picks the GitHub environment.
- With fnox and a store that CI cannot log into, such as Proton Pass, the job also sets `SECRETS_FROM_ENV: "1"`. The `with_*` wrappers then render empty, and the commands read the secrets that the steps map from GitHub. Without fnox, or with a [cloud secret manager](#secrets-from-a-cloud-secret-manager), the job does not set it.
- There is no `mise.ci.toml`: CI differs from a laptop only in where secrets come from.
- Runners install fnox and `pass-cli` from `[tools]`, although nothing calls them there. To skip the downloads, set `MISE_DISABLE_TOOLS: fnox,aqua:protonpass/pass-cli` on the workflow.

## Check workflow

```yaml
name: check
on:
  pull_request:
  push:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: jdx/mise-action@v5   # installs the tools; uses --locked when mise.lock exists
      - run: mise run setup
      - run: mise run check
```

- `check` needs no secrets and no environment: unit tests, lint, typecheck, and `tf:lint` all run without them. A test suite that needs a secret belongs in a separate job with an environment.
- `mise run setup` and `mise run check` are separate steps. `mise run setup ::: check` would run them in parallel.
- `mise generate github-action --write --task=check` writes a starting workflow. Review its triggers, action versions, and `env` before committing it.

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

jobs:
  apply:
    runs-on: ubuntu-latest
    environment: ${{ inputs.env }}              # GitHub environment: protection rules and its own secrets
    concurrency: terraform-${{ inputs.env }}    # never two applies against one state
    env:
      MISE_ENV: ${{ inputs.env }}               # loads mise.<env>.toml, like `mise -E <env>` locally
      SECRETS_FROM_ENV: "1"                     # with fnox: secrets come from the step, not Proton Pass
    steps:
      - uses: actions/checkout@v7
      - uses: jdx/mise-action@v5
      - run: mise run tf:apply                  # init, plan, print the plan, apply exactly that plan
        env:
          HCLOUD_TOKEN: ${{ secrets.HCLOUD_TOKEN }}
          TF_VAR_db_password: ${{ secrets.TF_VAR_db_password }}
          MISE_YES: "1"                         # accept the task's confirm prompt
```

- Create one GitHub environment per stack environment, with the same names (`development`, `staging`, `production`). Give `production` required reviewers. They approve the run before it starts, and the plan that it applies is printed in the step's log.
- The plan and the apply run in one step, so the plan file, which contains secrets in plain text, never leaves the runner.
- Only the apply step sets `MISE_YES`. Every other `confirm` in the run still fails without a terminal.
- A plan-only job has the same shape, with `mise run tf:plan` and no `MISE_YES`.
- `deploy` jobs follow the same shape: `MISE_ENV` on the job, and the secrets and `MISE_YES: "1"` on the `mise run deploy` step.

## Secrets in CI

- Store each secret as a **GitHub environment secret** with the same name as its variable. Each environment holds its own values, so a job for `development` cannot read production values, and `production`'s protection rules gate every job that can.
- Map secrets onto the **steps** that run tasks needing them, as above, not onto the whole job. Then checkout and other actions never see them.
- The names to map are the keys in the `with_<scope>_secrets` vars. When a key is added there, add it to every environment and to the workflow.
- Never define a variable in `[env]`, in `mise.toml` or in an environment file, that a step maps from secrets: mise's value would override the step's. Local defaults use `{ default = "..." }` ([mise.md](mise.md#environment-variables)).
- A secret missing from an environment arrives as an empty string, not an error. Terraform input variables reject empty values with a `validation` block (see [terraform.md](terraform.md#secrets)), and provider tokens fail at authentication.
- GitHub masks the values it injects in logs. GitHub shows secret names in upper case; the variable name in the workflow's `env` keeps its exact case (`TF_VAR_db_password`).
- CI never logs in to Proton Pass and has no Proton Pass token.

## Secrets from a cloud secret manager

With AWS Secrets Manager or GCP Secret Manager as the fnox backend ([secrets.md](secrets.md#cloud-secret-managers)), the job gets an identity instead of secrets, and the tasks read through fnox as they do on a laptop. GitHub stores no secret values, only each environment's role or service account as an environment variable (`vars`).

```yaml
jobs:
  apply:
    runs-on: ubuntu-latest
    environment: ${{ inputs.env }}
    concurrency: terraform-${{ inputs.env }}
    permissions:
      contents: read
      id-token: write                           # lets the job request an OIDC token for the cloud login
    env:
      MISE_ENV: ${{ inputs.env }}
    steps:
      - uses: actions/checkout@v7
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN }}   # set per GitHub environment; reads only acme-api/<env>/*
          aws-region: eu-central-1
      - uses: jdx/mise-action@v5
      - run: mise run tf:apply
        env:
          MISE_YES: "1"
```

- For GCP, replace the AWS step with `google-github-actions/auth@v3`, using `workload_identity_provider: ${{ vars.GCP_WORKLOAD_IDENTITY_PROVIDER }}` and `service_account: ${{ vars.GCP_SERVICE_ACCOUNT }}`. It sets up Application Default Credentials, which fnox's `gcp-sm` provider uses.
- The job sets no `SECRETS_FROM_ENV`, and the step maps no secrets.
- Restrict each role's or service account's trust to its GitHub environment through the OIDC subject (`repo:<org>/<repo>:environment:production`), so only jobs that passed production's protection rules can read production secrets.
- This workflow follows the action and fnox docs, with the action versions current in November 2026. It has not been run against a real account.

## Pull requests from forks

Fork pull requests receive no repository or environment secrets. That is fine, because the check workflow needs none. Never combine `pull_request_target` with a checkout of the fork's code in a job that holds secrets or an identity: the fork's code could read all of them.

## Monorepos

```yaml
      - run: mise run '//...:setup'
      - run: mise run '//...:check'
```

Keep `working_directory` unset so mise sees the monorepo root. `tf:*` tasks and the environment files stay at the root, so the Terraform workflow does not change.
