# Terraform

Terraform code lives in `terraform/` at the repository root. Each environment is its own root module with its own backend and state. The `tf:*` tasks are defined once in the repository-root `mise.toml` and take the environment as an argument.

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

- Directory names are exactly the environment names, so `tf:plan staging` maps to `terraform/environments/staging` with no lookup table.
- Shared logic goes in `terraform/modules/`. An environment directory holds only what differs: backend, provider config, module inputs, and sizes.
- Pin the Terraform version in `mise.toml` (`terraform = "1.17"`), and set `required_version` in each environment's `versions.tf` to match.
- Non-secret per-environment values go in that environment's `.tf` files or `terraform.tfvars`. Secret values come from fnox.

## Secrets

Terraform reads its credentials from environment variables. Locally, fnox supplies them from the environment's Proton Pass vault. In CI, the job sets them from the CI environment's secrets.

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

List the keys once, in the `with_tf_secrets` var, and use it in every task that talks to a provider or backend. A project without secrets drops the var and runs `terraform` directly. See [secrets.md](secrets.md) for the vault layout and the CI override.

## Tasks

Running these tasks against mise 2026.10.21 and fnox 1.43.0 confirmed the argument validation, the argument forwarding to `tf:init`, the per-environment vault selection, the CI override, and the confirmation behavior. Replace the example keys in `with_tf_secrets` with the project's own.

```toml
[vars]
tf_dir = "terraform/environments"
# Prefix for Terraform commands that need secrets. Locally, fnox reads them from the vault
# of the profile in FNOX_PROFILE. mise.ci.toml empties it, because CI sets them itself.
with_tf_secrets = "fnox exec --only HCLOUD_TOKEN,TF_VAR_db_password --if-missing error --"

[task_templates.env-arg]
usage = '''
arg "<env>" help="Target environment" {
  choices "development" "staging" "production"
}
'''

[tasks."tf:init"]
description = "Initialize Terraform for an environment"
extends = "env-arg"
run = "FNOX_PROFILE={{ usage.env }} {{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ usage.env }} init -input=false"

[tasks."tf:plan"]
description = "Plan Terraform changes for an environment and save them to tfplan"
extends = "env-arg"
depends = [{ task = "tf:init", args = ["{{ usage.env }}"] }]
run = "FNOX_PROFILE={{ usage.env }} {{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ usage.env }} plan -input=false -out=tfplan"

[tasks."tf:apply"]
description = "Apply the saved Terraform plan to an environment"
extends = "env-arg"
confirm = "Apply the saved Terraform plan to {{ usage.env }}?"
run = "FNOX_PROFILE={{ usage.env }} {{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ usage.env }} apply -input=false tfplan"

[tasks."tf:destroy"]
description = "Destroy every resource in an environment"
extends = "env-arg"
interactive = true   # Terraform asks for "yes" itself
depends = [{ task = "tf:init", args = ["{{ usage.env }}"] }]
run = "FNOX_PROFILE={{ usage.env }} {{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ usage.env }} destroy"

[tasks."tf:output"]
description = "Print Terraform outputs for an environment"
extends = "env-arg"
run = "FNOX_PROFILE={{ usage.env }} {{ vars.with_tf_secrets }} terraform -chdir={{ vars.tf_dir }}/{{ usage.env }} output"

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

`tf:lint` and `tf:format` need no secrets: `init -backend=false` downloads providers without touching state. That lets them run in pull-request CI without any secrets.

## Plan and apply

`tf:plan` saves the plan, and `tf:apply` applies exactly that file:

```sh
mise run tf:plan staging      # review the output
mise run tf:apply staging     # confirm; applies the reviewed plan
```

- What was reviewed is what gets applied. If state changed in between, Terraform rejects the stale plan and you plan again.
- `tf:apply` without a preceding plan fails with `stat tfplan: no such file or directory`. Run `tf:plan` first.
- `confirm` makes local applies deliberate. In CI the apply step sets `MISE_YES=1` (see [ci.md](ci.md)), and the CI system's environment protection decides who may run it.
- **A plan file contains secret values in plain text.** It stays in the environment directory, is gitignored, and is never uploaded as a CI artifact. In CI, plan and apply run in the same job.
- Agents run `tf:plan` against staging or production only when asked, because it reads real state with real credentials. They never run `tf:apply` or `tf:destroy` unless the user explicitly requests that apply.

## TFLint

When a project uses TFLint, add `tflint = "0.65"` to `[tools]`, keep the config in `terraform/.tflint.hcl`, and extend `tf:lint` with:

```bash
tflint --chdir=terraform --init
tflint --chdir=terraform --recursive
```

This was tested with TFLint 0.65. TFLint exits non-zero when it finds issues, so `tf:lint`, and therefore `check`, fails on them.

## Adding an environment

1. Create `terraform/environments/<env>/` with its own backend.
2. Add `<env>` to the `choices` in the `env-arg` template. All environment tasks follow.
3. Add `[profiles.<env>.providers.protonpass]` in `fnox.toml` with the vault `<project>-<env>`, and create that vault and its items in Proton Pass.
4. Create a GitHub environment with the same name and the same secret names, and add `<env>` to the workflow's `options` (see [ci.md](ci.md)).

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
