# Terraform

Terraform code lives in `terraform/` at the repository root. Each environment is its own root module with its own backend and state. The `tf:*` tasks are defined once in the repository-root `mise.toml` and act on the environment selected with `mise -E <env>` (see [mise.md](mise.md#environments)).

## Contents

- [Layout](#layout)
- [Secrets](#secrets)
- [Tasks](#tasks)
- [Plan and apply](#plan-and-apply)
- [TFLint](#tflint)
- [Adding an environment](#adding-an-environment)
- [Ignore and commit](#ignore-and-commit)

## Layout

```text
mise.development.toml        # DEPLOY_ENV = "development", and with fnox FNOX_PROFILE
mise.staging.toml
mise.production.toml
terraform/
├── modules/
│   └── <module>/            # reusable modules; no backend, no provider credentials
└── environments/
    ├── development/         # root module: backend, providers, module calls, env values
    │   ├── main.tf
    │   ├── backend.tf
    │   ├── versions.tf
    │   └── .terraform.lock.hcl
    ├── staging/
    └── production/
```

- Directory names are exactly the environment names, so `mise -E staging run tf:plan` maps to `terraform/environments/staging` with no lookup table.
- Shared logic goes in `terraform/modules/`. An environment directory holds only what differs: backend, provider config, module inputs, and sizes.
- Pin the Terraform version in `mise.toml` (`terraform = "1.17"`), and set `required_version` in each environment's `versions.tf` to match.
- Non-secret per-environment values go in that environment's `.tf` files or `terraform.tfvars`, not in `mise.<env>.toml`, so Terraform run by hand sees the same values. Secret values come from fnox locally and from the platform's secret store in CI.

## Secrets

Terraform reads its credentials from environment variables. Locally, fnox supplies them from the selected environment's vault. In CI, the job provides them (see [ci.md](ci.md#secrets-in-ci)).

- Provider credentials use the provider's standard variable (`HCLOUD_TOKEN`, `CLOUDFLARE_API_TOKEN`, `AWS_ACCESS_KEY_ID`, ...).
- Backend credentials work the same way, for example S3-compatible state storage keys.
- Secret input variables are named `TF_VAR_<variable>`, and Terraform reads them without `-var` flags. Declare such variables with `sensitive = true` and reject empty values, because a secret missing from a GitHub environment arrives as an empty string:

```hcl
variable "db_password" {
  type      = string
  sensitive = true
  validation {
    condition     = length(var.db_password) > 0
    error_message = "db_password is empty. Set TF_VAR_db_password."
  }
}
```

List the keys once, in the `with_tf_secrets` var, and use it in every task that talks to a provider or backend. A project without secrets drops the var and runs `terraform` directly. See [secrets.md](secrets.md) for the vault layout and `SECRETS_FROM_ENV`.

## Tasks

Running these tasks against mise 2026.11.2, fnox 1.47.0, and Terraform 1.17.1 confirmed the missing-environment error, the per-environment directory and secrets, the confirmation after the plan, and the commands without fnox under `SECRETS_FROM_ENV=1`. Replace the example keys in `with_tf_secrets` with the project's own.

```toml
[env]
DEPLOY_ENV = false   # only mise.<env>.toml selects an environment

[vars]
tf_dir = "terraform/environments"
# Prefix for Terraform commands that need secrets. Locally, fnox reads them from the vault of the
# selected environment (FNOX_PROFILE in mise.<env>.toml). Where SECRETS_FROM_ENV is set, as in CI,
# it renders empty and Terraform reads the variables the caller provides.
with_tf_secrets = "{% if env.SECRETS_FROM_ENV is undefined %}fnox exec --only HCLOUD_TOKEN,TF_VAR_db_password --if-missing error --{% endif %}"

[task_templates.deployed]
env = { DEPLOY_ENV = { required = "Select an environment: mise -E <development|staging|production> run <task>" } }

[tasks."tf:init"]
description = "Initialize Terraform for the selected environment"
extends = "deployed"
run = "{{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ env.DEPLOY_ENV }} init -input=false"

[tasks."tf:plan"]
description = "Plan Terraform changes for the selected environment"
extends = "deployed"
depends = ["tf:init"]
run = "{{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ env.DEPLOY_ENV }} plan -input=false -out=tfplan"

[tasks."tf:apply"]
description = "Plan, confirm, and apply Terraform changes to the selected environment"
extends = "deployed"
depends = ["tf:plan"]
confirm = "Apply this plan to {{ env.DEPLOY_ENV }}?"
run = "{{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ env.DEPLOY_ENV }} apply -input=false tfplan"

[tasks."tf:destroy"]
description = "Destroy every resource in the selected environment"
extends = "deployed"
interactive = true   # Terraform asks for "yes" itself
depends = ["tf:init"]
run = "{{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ env.DEPLOY_ENV }} destroy"

[tasks."tf:output"]
description = "Print Terraform outputs for the selected environment"
extends = "deployed"
run = "{{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ env.DEPLOY_ENV }} output"

[tasks."tf:lint"]
description = "Check Terraform formatting and validate every environment"
run = '''
#!/usr/bin/env bash
set -euo pipefail
terraform fmt -check -recursive terraform
for dir in {{ vars.tf_dir }}/*/; do
  terraform -chdir="$dir" init -backend=false -input=false >/dev/null
  terraform -chdir="$dir" validate
done
'''

[tasks."tf:format"]
description = "Format all Terraform files"
run = "terraform fmt -recursive terraform"
```

Wire them into the lifecycle tasks: root `lint` gets `depends = ["tf:lint"]`, and root `format` gets `depends = ["tf:format"]`. In a repository that is only Terraform, `lint` and `format` simply depend on these, and `check` depends on `lint`.

`tf:lint` and `tf:format` do not extend `deployed` and need no secrets: they cover every environment at once, and `init -backend=false` downloads providers without touching state. That lets them run in pull-request CI without an environment.

## Plan and apply

`tf:apply` is one command. It initializes, plans, prints the plan, asks, and applies exactly the plan it printed:

```sh
mise -E staging run tf:apply   # plan, review, answer y, done
mise -E staging run tf:plan    # only see what would change
```

- `tf:apply` depends on `tf:plan`, which saves the plan to `tfplan`. mise asks `Apply this plan to staging?` after the plan has printed, and the apply step applies that file. What you confirm is what gets applied. If state changed in between, Terraform rejects the stale plan, and you run `tf:apply` again.
- Answering no fails the task with `aborted by user` and changes nothing. A plan with no changes still asks, and applying it changes nothing.
- Run `tf:plan` alone to review changes without applying them, for example while writing Terraform code.
- Without a terminal, the task stops after the plan with `task requires confirmation but there was nobody to ask`. In CI the apply step sets `MISE_YES=1` (see [ci.md](ci.md)), and the CI system's environment protection decides who may run it.
- **A plan file contains secret values in plain text.** It stays in the environment directory, is gitignored, and is never uploaded as a CI artifact. In CI, the plan and the apply run in one step.
- Agents run `tf:plan` against staging or production only when asked, because it reads real state with real credentials. They never run `tf:apply` or `tf:destroy` with a deployed environment selected unless the user explicitly requests that apply.

## TFLint

When a project uses TFLint, add `tflint = "0.65"` to `[tools]`, keep the config in `terraform/.tflint.hcl`, and extend `tf:lint` with:

```bash
tflint --chdir=terraform --init
tflint --chdir=terraform --recursive
```

This was tested with TFLint 0.65. TFLint exits non-zero when it finds issues, so `tf:lint`, and therefore `check`, fails on them.

## Adding an environment

1. Create `terraform/environments/<env>/` with its own backend.
2. Create `mise.<env>.toml` with `DEPLOY_ENV = "<env>"` and, with fnox, `FNOX_PROFILE = "<env>"`, plus the environment's non-secret settings. Add `<env>` to the help text of the `deployed` template.
3. With fnox, add `[profiles.<env>.providers.<provider>]` in `fnox.toml` with that environment's vault, account, or project, and create it and its secrets in the backend.
4. Create a GitHub environment with the same name and the same secret names, or with a cloud secret manager the identity for that environment, and add `<env>` to the workflow's `options` (see [ci.md](ci.md)).

Use the full names `development`, `staging`, `production` for the standard environments. A new environment name must be the same string everywhere.

## Ignore and commit

```gitignore
# Terraform
.terraform/
tfplan
*.tfstate
*.tfstate.*
crash.log
```

Commit each environment's `.terraform.lock.hcl` so provider versions and checksums match across machines.
