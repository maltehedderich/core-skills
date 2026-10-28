# Secrets with fnox

fnox is optional. Add it when a command that developers run locally needs a secret: Terraform credentials, a deploy token, or a deployed environment's database URL. A project whose tasks need no secrets has no `fnox.toml`, and fnox and `pass-cli` stay out of `mise.toml`.

Verified against fnox 1.43.0 and pass-cli 2.5.1. When a detail matters and may have changed, check the current docs (Context7 library `/jdx/fnox`, or https://fnox.jdx.dev).

## Contents

- [Where secrets come from](#where-secrets-come-from)
- [Proton Pass layout](#proton-pass-layout)
- [fnox.toml](#fnoxtoml)
- [Other backends](#other-backends)
- [Secrets in tasks](#secrets-in-tasks)
- [Local setup](#local-setup)
- [Add a secret](#add-a-secret)
- [Agent tokens](#agent-tokens)
- [Troubleshooting](#troubleshooting)
- [Rules](#rules)

## Where secrets come from

| Where the task runs | Source | How the command gets them |
| --- | --- | --- |
| Developer machine or agent | Proton Pass, read by fnox through `pass-cli` | The task wraps its command in `fnox exec`, which resolves only the listed keys from the environment's vault. |
| CI | The CI system's secret store, such as GitHub environment secrets | The job sets them as environment variables. `MISE_ENV=ci` loads `mise.ci.toml`, which removes the fnox wrapper, so the command reads them directly. |

Every source uses the same variable names, so the command never knows where a value came from. `fnox.toml` holds references only (vault, item, field) and is committed. The values never touch the repository.

fnox resolves a secret from its provider first. A value already set in the environment does not override the provider, and if the provider fails, fnox does not fall back to the environment variable. That is why CI skips fnox instead of running it next to GitHub's secrets.

## Proton Pass layout

Proton Pass is the default backend. Use another one only when the project already uses it or the user asks for it (see [Other backends](#other-backends)).

- **One vault per project and environment**: `<project>-development`, `<project>-staging`, `<project>-production` (for example `acme-api-production`). Vault membership decides who can read production. An fnox profile only chooses configuration and restricts nobody.
- **One item per secret, named exactly like the environment variable**: an item `HCLOUD_TOKEN` whose `password` field holds the value. Every vault then has the same item names, `fnox.toml` lists each secret once, and anyone can find a variable's source by its name.
- Use another field only for multi-field items (`value = "DATABASE/username"`). Use a full `pass://vault/item/field` reference only when a name contains `/`.
- The Proton Pass provider is **read-only**. `fnox set` cannot write to it, so create and edit items in the Proton Pass app or with `pass-cli`.

## fnox.toml

The top level describes development use. Each environment gets a profile whose only change is the vault. Profiles inherit every top-level secret, and a profile's `protonpass` provider replaces the top-level one by name, so the same item names resolve from that environment's vault. Define `development` explicitly even though it repeats the top level: tasks select a profile for every environment, and an undefined profile is an error (`Profile 'development' not found`).

```toml
#:schema https://fnox.jdx.dev/schema.json
# Secret values live in Proton Pass; this file holds references only.
# Vaults: acme-api-development, acme-api-staging, acme-api-production.
# CI does not use this file: its secrets come from GitHub environment secrets.
if_missing = "error"   # fail before the command starts when a requested secret can't be read
env = "exec"           # inject only into `fnox exec` commands, never into an interactive shell
redact_exec = true     # replace secret values in piped `fnox exec` output with [REDACTED]

[providers.protonpass]
type = "proton-pass"
vault = "acme-api-development"

[secrets]
HCLOUD_TOKEN = { provider = "protonpass", value = "HCLOUD_TOKEN", description = "Hetzner Cloud API token for Terraform" }
TF_VAR_db_password = { provider = "protonpass", value = "TF_VAR_db_password", description = "Database admin password" }
DATABASE_URL = { provider = "protonpass", value = "DATABASE_URL", description = "Application database connection string" }

[profiles.development.providers.protonpass]
type = "proton-pass"
vault = "acme-api-development"

[profiles.staging.providers.protonpass]
type = "proton-pass"
vault = "acme-api-staging"

[profiles.production.providers.protonpass]
type = "proton-pass"
vault = "acme-api-production"
```

With a stubbed `pass-cli`, this resolves `HCLOUD_TOKEN` to `pass://acme-api-staging/HCLOUD_TOKEN/password` for the `staging` profile and to `pass://acme-api-production/HCLOUD_TOKEN/password` for `production`.

- Give every secret a `description`. `fnox list` shows it, and it tells the next person what the item is for.
- `redact_exec` matters for agents: their commands run with piped output, so a value that a command prints shows up as `[REDACTED]`.
- A value that differs between environments in more than its vault gets an override under `[profiles.<env>.secrets]`.
- `fnox.local.toml` (gitignored) holds personal overrides, such as a local `DATABASE_URL`. A top-level secret there overrides that secret in every profile. Put it under `[profiles.<env>.secrets]` to override one profile only.
- In a monorepo, put the provider and profiles in the root `fnox.toml` and each service's secrets in its own `fnox.toml`. fnox merges the files from the current directory upward.

## Other backends

fnox supports many providers, including 1Password, Bitwarden, age, AWS Secrets Manager, HashiCorp Vault, and the macOS keychain (`fnox provider add --help` lists them all). When the project already uses one, or the user names one, keep everything else in this reference and change only:

- **The provider blocks**: `type` and its settings at the top level and in each `[profiles.<env>.providers.<name>]`. Name the provider after the backend (`onepassword`, `bitwarden`) and use that name in each secret's `provider`.
- **The `value` references**, in the format the provider's page gives.
- **The CLI in `mise.toml`**, if the provider needs one, instead of `pass-cli`. Find its mise name with `mise registry <name>`.
- **The login steps** in [Local setup](#local-setup).

Keep one store, vault, or project per environment where the backend supports it, so access to production stays separate. Read the provider's page (https://fnox.jdx.dev/providers/overview) before writing its configuration. The task wrappers, `mise.ci.toml`, and CI do not change.

## Secrets in tasks

A task gets secrets only by wrapping its command in `fnox exec`. Write the wrapper once per group of commands that need the same keys, as a `[vars]` entry named `with_<scope>_secrets`, and empty it in `mise.ci.toml`:

```toml
# mise.toml
[vars]
# Prefix for commands that need these secrets. Locally, fnox reads them from the vault
# of the profile in FNOX_PROFILE. mise.ci.toml empties it, because CI sets them itself.
with_db_secrets = "fnox exec --only DATABASE_URL --if-missing error --"

[tasks."db:migrate"]
description = "Apply pending database migrations"
usage = '''
arg "[env]" help="Target environment; omit for local" {
  choices "development" "staging" "production"
}
'''
run = '''
#!/usr/bin/env bash
set -euo pipefail
if [ -z "${usage_env:-}" ]; then
  exec uv run alembic upgrade head                 # local database, no secrets
fi
FNOX_PROFILE="$usage_env" exec {{ vars.with_db_secrets }} uv run alembic upgrade head
'''
```

```toml
# mise.ci.toml, loaded when MISE_ENV=ci
# CI sets secrets from its own secret store, so commands run without fnox.
[vars]
with_db_secrets = ""

[settings]
disable_tools = ["fnox", "aqua:protonpass/pass-cli"]
```

Tested with mise 2026.10.21 and fnox 1.43.0: locally, `db:migrate production` read from the production vault, and `tf:output staging` read from the staging vault even with `FNOX_PROFILE=production` set in the calling shell. With `MISE_ENV=ci`, the same tasks ran without fnox and used the variables that CI provided.

- **The task sets `FNOX_PROFILE` on the command line** (`FNOX_PROFILE={{ usage.env }}` in a one-line `run`, `FNOX_PROFILE="$usage_env"` in a script). It overrides whatever the developer's shell has. In CI, the assignment is harmless. Do not put `$usage_env` inside a `[vars]` value: mise expands `$NAME` in config values when it loads them, before any task runs.
- **`--only KEY1,KEY2`** resolves only what the command needs. Every resolved key is a read from the vault, so this keeps tasks fast, keeps the access log meaningful, and limits what a command could leak. A name or glob that matches no secret in `fnox.toml` is an error, so list only keys that exist.
- **`--if-missing error`** repeats the config default, so the task stays safe even if someone relaxes `if_missing`.
- **The calling shell expands `$VARS` before fnox runs**, so `fnox exec -- echo $DATABASE_URL` prints an empty value. Inside a shell expression, start a child shell with a single-quoted script: `{{ vars.with_db_secrets }} sh -c 'psql "$DATABASE_URL" -c "select 1"'`.
- **Every key in a `with_*` var must also exist in each GitHub environment** that runs the task (see [ci.md](ci.md#secrets-in-ci)).
- For an ad hoc command outside tasks: `mise exec -- fnox exec -P development --only DATABASE_URL -- <cmd>`.

## Local setup

Each developer, once per machine:

```sh
mise install                         # installs fnox and pass-cli from mise.toml
mise exec -- pass-cli login          # browser login; the session persists
mise exec -- pass-cli info           # confirm the session
mise exec -- fnox provider test protonpass
mise exec -- fnox check --all -P development   # every secret resolves; prints no values
```

A locked session needs `pass-cli session unlock`. Each developer also needs read access to the vaults of the environments they work on.

## Add a secret

1. Create an item named after the variable in each environment's vault that needs it, with the value in the `password` field. You do this in Proton Pass, not with fnox. If you cannot do it yourself, list the vaults and item names for the user.
2. Add the line to `[secrets]` in `fnox.toml`, with a `description`.
3. Add the key to the `--only` list in the `with_<scope>_secrets` var of each task group that needs it.
4. Add a secret with the same name to each GitHub environment whose jobs run those tasks, and map it in the workflow step's `env` (see [ci.md](ci.md#secrets-in-ci)).
5. Check without printing values: `mise exec -- fnox check --all -P development`. Check staging and production only when the user asks, because those reads appear in the vault's access log.

Secrets that Terraform reads as input variables are named `TF_VAR_<variable>` (see [terraform.md](terraform.md#secrets)).

## Agent tokens

When an AI agent uses a Proton Pass agent token (a personal access token with access logging), `pass-cli` requires a reason for every read. Set it for the agent's session with `FNOX_PROTON_PASS_AGENT_REASON="<what and why>"`, or add `agent_reason = "<text>"` (at most 300 characters) to the provider. Personal browser sessions do not need it.

## Troubleshooting

| Message | Cause and fix |
| --- | --- |
| `This operation requires an authenticated client` | No `pass-cli` session. Run `mise exec -- pass-cli login`. |
| `Could not find vault <name>` | The vault name is wrong, or this account cannot see it. Compare against the Proton Pass app and check vault membership. |
| `Field does not exist` | The item has no field with that name. Use `password`, or name the right field after the `/`. |
| `Profile '<x>' not found` | No `[profiles.<x>]` section, or a misspelled environment. Use the full environment names. |
| `fnox env cannot provide: unknown keys: <pattern>` | An `--only` name or glob matches no secret in `fnox.toml`. |
| `Agent reason required` | Agent token without a reason. See [Agent tokens](#agent-tokens). |
| `Could not get local key from keyring` | `pass-cli` cannot read its session key, which is common on headless Linux. Check `PROTON_PASS_KEY_PROVIDER` (`fs`, `env`, `keyring`) and `PROTON_PASS_SESSION_DIR` in the pass-cli docs. |
| Session locked | `pass-cli session unlock`. |
| A task in CI calls fnox | The job does not set `MISE_ENV=ci`, or `mise.ci.toml` misses that `with_*` var. |

Narrow problems layer by layer: `mise exec -- fnox --version` (installed?), `mise exec -- fnox config-files` (config found?), `mise exec -- fnox list -P <env>` (secret defined?), `mise exec -- fnox check --all -P <env>` (resolvable?).

## Rules

- Never put a secret value in `mise.toml`, `[env]`, a committed `.env`, a task's command line, a `default =` in `fnox.toml`, or a log. `default` values are plain text and only for non-secrets.
- Never print secret values to check them. `fnox check` and `fnox list` are enough. Do not run `fnox get` or `fnox export` unless the user asks for the value itself.
- Never commit `fnox.local.toml` or `.fnox.local.toml`.
- Do not use `fnox activate` in shells. `env = "exec"` keeps secrets out of interactive shells regardless.
- CI never logs in to Proton Pass. Its secrets live in the CI system's secret store.
