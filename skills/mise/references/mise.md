# mise: tools, environment, and tasks

Verified against mise 2026.10.21. When a detail matters and may have changed, check the current docs (Context7 library `/jdx/mise`, or https://mise.jdx.dev).

## Contents

- [Files](#files)
- [Base configuration](#base-configuration)
- [Tools and the lockfile](#tools-and-the-lockfile)
- [Python with uv](#python-with-uv)
- [JavaScript and TypeScript with bun](#javascript-and-typescript-with-bun)
- [Environment variables](#environment-variables)
- [Tasks](#tasks)
- [Monorepos](#monorepos)
- [The ci config environment](#the-ci-config-environment)
- [Trust and shell activation](#trust-and-shell-activation)
- [Pitfalls](#pitfalls)
- [Deliberately not used](#deliberately-not-used)

## Files

| File | Commit? | Purpose |
| --- | --- | --- |
| `mise.toml` | Yes | Tools, settings, non-secret env, vars, task templates, tasks. |
| `mise.lock` | Yes | Exact tool versions, URLs, and checksums for every platform. |
| `mise-tasks/` | Yes | File tasks: one script per task, named by path. |
| `mise.ci.toml` | Yes | CI differences, loaded with `MISE_ENV=ci`. Only projects with fnox need it. See [ci.md](ci.md#the-ci-config-environment). |
| `mise.local.toml`, `mise.*.local.toml` | No | Personal overrides. Add both patterns to `.gitignore`. |

Keep tool versions only in `mise.toml`. When adopting the stack, remove `.tool-versions`, `.nvmrc`, `.node-version`, `.python-version`, `.terraform-version`, and `.bun-version` after moving their versions into `[tools]`. Two sources of truth eventually disagree. A stale `.python-version` also makes uv request an interpreter mise did not install.

## Base configuration

Assemble `mise.toml` in this order. Include only the sections the project needs.

```toml
min_version = "2026.10.0"   # the mise version the config was written with (`mise --version`)

[settings]
lockfile = true                    # create and update mise.lock automatically
python.uv_venv_auto = "source"     # Python projects only: activate uv's .venv

[tools]
python = "3.14"                    # Python projects
uv = "0.13"                        # Python projects
bun = "1.4"                        # JavaScript/TypeScript projects
terraform = "1.17"                 # projects with terraform/
fnox = "1.43"                      # only when tasks need secrets locally
"aqua:protonpass/pass-cli" = "2.5" # with fnox's default Proton Pass backend

[env]
UV_PYTHON_PREFERENCE = "only-system" # Python projects: uv uses the Python mise puts on PATH

[vars]
# Values for templates; see terraform.md.

[task_templates.env-arg]
usage = '''
arg "<env>" help="Target environment" {
  choices "development" "staging" "production"
}
'''

[tasks.setup]
description = "Install project dependencies from the lockfiles"
run = "uv sync --locked"
```

The versions above were current in October 2026. For a new project, ask mise for today's versions (`mise latest terraform`) and write the major.minor, as above, rather than copying these.

## Tools and the lockfile

- **Request major.minor, lock the exact version.** `terraform = "1.17"` accepts any 1.17.x. `mise.lock` records the exact patch release and checksums, so every machine and CI runner installs the same binary. For Python and Terraform, the minor version is the compatibility boundary that matters.
- `mise use terraform@1.17` adds a tool. `mise install` installs everything. `mise run` installs missing tools before it starts a task.
- `mise lock` writes `mise.lock`. With `lockfile = true` it already covers the common platforms (Linux, macOS, Windows, x64 and arm64), so macOS laptops and Linux runners share one file.
- `mise install --locked` installs exactly what the lockfile records. `jdx/mise-action` adds `--locked` itself when the repository has a `mise.lock`.
- To upgrade: `mise lock --bump terraform`, then `mise install --locked`, review the lockfile diff, run `mise run check`, and commit both files. To cross a minor version, change the request in `mise.toml` first.
- `mise.lock` covers tools only. Also keep `uv.lock`, `bun.lock`, and Terraform's `.terraform.lock.hcl`.

Registry names for the stack:

| Tool | `[tools]` key | Notes |
| --- | --- | --- |
| Python | `python` | Precompiled builds. |
| uv | `uv` | |
| bun | `bun` | Provides `bun` and `bunx`. |
| Node.js | `node` | Only when a dependency needs the Node runtime. |
| Terraform | `terraform` | aqua backend, checksum-verified. |
| TFLint | `tflint` | Optional, see [terraform.md](terraform.md#tflint). |
| fnox | `fnox` | Optional, see [secrets.md](secrets.md). |
| Proton Pass CLI | `"aqua:protonpass/pass-cli"` | For fnox's Proton Pass backend. Not in mise's short-name registry; the aqua package provides `pass-cli`. |

## Python with uv

mise installs Python and uv. uv owns the project environment and dependencies. Neither pip, pipx, poetry, nor `python -m venv` is used.

```toml
[settings]
python.uv_venv_auto = "source"

[tools]
python = "3.14"
uv = "0.13"

[env]
UV_PYTHON_PREFERENCE = "only-system"
```

- `UV_PYTHON_PREFERENCE = "only-system"` stops uv from downloading or choosing its own Python, so it uses the interpreter mise put on `PATH`. mise's docs also show `UV_PYTHON = { value = "{{ tools.python.path }}", tools = true }`. Don't use that template: before `mise install` has run, as on a fresh clone, it makes every `mise run` and `mise tasks` command fail with `Field python is not defined`.
- `python.uv_venv_auto = "source"` activates `.venv` in mise-activated shells and tasks once `uv.lock` exists. `setup` creates it.
- `requires-python` in `pyproject.toml` states compatibility; `[tools] python` picks the interpreter. Delete the `.python-version` that `uv init` writes.
- Tasks call tools through uv: `uv run pytest`, `uv run ruff check .`. `uv run` syncs the environment first.
- Add dependencies with `uv add <pkg>` / `uv add --dev <pkg>`. They update `uv.lock`, which `setup` then installs with `--locked`.
- For a standalone helper script with dependencies, write a file task with a `#!/usr/bin/env -S uv run --script` shebang and a PEP 723 block.

Typical Python tasks:

```toml
[tasks.setup]
description = "Install project dependencies from the lockfiles"
run = "uv sync --locked"

[tasks.lint]
description = "Run read-only static checks"
run = ["uv run ruff check .", "uv run ruff format --check ."]

[tasks.format]
description = "Format code and apply safe lint fixes"
run = ["uv run ruff check --fix .", "uv run ruff format ."]

[tasks.typecheck]
description = "Type-check the code"
run = "uv run mypy src"

[tasks.test]
description = "Run the test suite"
run = "uv run pytest"
```

## JavaScript and TypeScript with bun

bun is the runtime, package manager, and test runner. npm, yarn, and pnpm are not used. Add `node` only when a dependency truly needs the Node runtime.

```toml
[tools]
bun = "1.4"

[tasks.setup]
description = "Install project dependencies from the lockfiles"
run = "bun install --frozen-lockfile"

[tasks.dev]
description = "Run the app locally with reload"
run = "bun run dev"

[tasks.build]
description = "Build the app"
run = "bun run build"

[tasks.test]
description = "Run the test suite"
run = "bun test"

[tasks.typecheck]
description = "Type-check the code"
run = "bunx tsc --noEmit"
```

- mise tasks are the interface. Frameworks often expect `package.json` scripts (`dev`, `build`). Keep those scripts, give them canonical names, and have the mise task call `bun run <same-name>`. Do not create package scripts that duplicate mise tasks under other names.
- Commit `bun.lock`. Add packages with `bun add` / `bun add -d`.

## Environment variables

`[env]` holds only non-secret configuration, such as `LOG_LEVEL` or `UV_PYTHON_PREFERENCE`. mise loads `[env]` into every task, shell, and `mise env` output, so it is no place for secrets. Locally, secrets come from fnox at the moment a task needs them. In CI, they come from the CI system's secret store (see [secrets.md](secrets.md)). Do not load `.env` files with `_.file` unless they contain only non-secret defaults.

`[vars]` holds values that only templates need, such as paths and key lists. Vars are not exported to processes.

## Tasks

### TOML tasks or file tasks

Write short commands as TOML tasks in `mise.toml`. Move a recipe longer than about five lines into a file task: an executable script in `mise-tasks/`, named by its path. `mise-tasks/db/migrate` becomes `db:migrate`. A `_default` file takes its directory's name. File tasks declare metadata in comments:

```bash
#!/usr/bin/env bash
#MISE description="Apply pending database migrations"
#USAGE arg "[env]" help="Target environment; omit for local" {
#USAGE   choices "development" "staging" "production"
#USAGE }
set -euo pipefail
...
```

Make the file executable (`chmod +x`). A multi-line `run` with a shebang line also works inside TOML (see `tf:lint` in [terraform.md](terraform.md)).

### Task fields used in this stack

| Field | Use |
| --- | --- |
| `description` | Required on every task. |
| `run` | A string, or an array of commands that run in order and stop at the first failure. Entries can be `{ task = "name", args = [...] }`. |
| `depends` | Tasks that finish first. Shared dependencies run once, independent ones in parallel. Pass arguments: `{ task = "tf:init", args = ["{{ usage.env }}"] }`. |
| `usage` | Arguments and flags. Values reach the command as `{{ usage.name }}` (rendered before the shell runs) and `$usage_name`. |
| `extends` | Inherit from a `[task_templates.<name>]`. `usage` specs merge, and the template's arguments come first. |
| `confirm` | Prompt before the task's own command runs (after its `depends`). |
| `interactive` | Give the task the terminal, for commands that prompt, such as `terraform destroy`. |
| `dir` | Working directory. The default is the config root. Prefer the tool's own flag where one exists, such as `terraform -chdir=`. |
| `sources` / `outputs` | Skip the task while its outputs are newer than its sources. |
| `hide` | Hide helper tasks from listings. |
| `vars` | Task-level overrides of `[vars]`. |

### Environment argument

Define the environment argument once and extend it, so every environment task validates against the same list:

```toml
[task_templates.env-arg]
usage = '''
arg "<env>" help="Target environment" {
  choices "development" "staging" "production"
}
'''

[tasks.deploy]
description = "Deploy the application to an environment"
extends = "env-arg"
confirm = "Deploy to {{ usage.env }}?"
run = "./scripts/deploy.sh {{ usage.env }}"
```

`mise run deploy prod` fails with `Invalid choice for arg env: prod, expected one of development, staging, production`, and `mise run deploy --help` lists the choices. Templates cannot set `interactive`, `hide`, or `secrets`; set those on each task. For an optional environment, write `arg "[env]"` in the task's own `usage` instead of extending the template.

### Confirmation

```toml
confirm = "Apply the saved Terraform plan to {{ usage.env }}?"
```

Without a terminal, as in CI, a task with `confirm` fails with `task requires confirmation but there was nobody to ask; pass --yes to accept`. CI sets `MISE_YES=1` on the steps that are allowed to proceed.

### Running tasks

```sh
mise tasks ls                    # names and descriptions
mise tasks info tf:plan          # the merged definition, including template fields
mise tasks validate              # config errors in every task
mise run tf:plan --help          # arguments and choices
mise run -n tf:plan staging      # dry run: print the commands in order, run nothing
mise run test -- -k smoke        # pass arguments through to the command
mise run lint ::: test           # several tasks, in parallel unless one depends on the other
```

Put mise's own flags before the task name. Everything after the name belongs to the task. Write `mise run <task>`, not the `mise <task>` shorthand, in scripts and docs: a future mise subcommand could take the task's name.

## Monorepos

```toml
# repository-root mise.toml
monorepo_root = true

[monorepo]
config_roots = ["services/*", "web"]
```

- Each listed directory has its own `mise.toml` with bare canonical task names. mise names them `//services/api:test` and so on.
- `mise run '//...:check'` runs `check` in every project (quote the pattern). Inside a project, `mise run :test` targets the nearest project.
- Tools and `[env]` from the root config apply to every project. A project can override them.
- `mise install --monorepo` installs every project's tools, which is useful for warming CI caches.
- Keep `tf:*` tasks and the fnox source in the repository root.

## The ci config environment

`MISE_ENV=ci` makes mise load `mise.ci.toml` on top of `mise.toml`. Every workflow sets it. In this stack, `mise.ci.toml` empties the fnox wrappers and skips installing fnox and `pass-cli`, because CI gets secrets from its own secret store. See [ci.md](ci.md#the-ci-config-environment).

Do not create config environments for the deployment environments (`mise.production.toml`). The deployment environment is a task argument, so one checkout can plan staging and production without switching config.

## Trust and shell activation

- mise asks you to trust a project's config before using it: run `mise trust` after cloning. In CI, mise trusts the checked-out config automatically.
- Shell activation is for interactive convenience only: `eval "$(mise activate zsh)"` in `~/.zshrc` puts tools and the venv on `PATH` when you `cd` into a project. Tasks, CI, and agents use `mise run` or `mise exec -- <cmd>` and do not need it.

## Pitfalls

- mise expands `$NAME` in `[env]` and `[vars]` values when it loads the config, before any task runs. A `$usage_env` in a var stays unexpanded and prints a warning. Use `{{ usage.env }}` or `$usage_env` in the task's own `run` instead.
- `{{ tools.<name>.path }}` in `[env]` breaks every command until that tool is installed. Avoid tool-path templates in shared config.
- Glob patterns in `mise run` need quotes (`mise run 'test:*'`), or the shell expands them.
- A task with `confirm` needs a terminal or `MISE_YES=1`.
- `run` is rendered by Tera before the shell sees it. To pass a literal `{{`, wrap it in `{% raw %}...{% endraw %}`.
- Wildcard `depends` (`lint:*`) fails when nothing matches unless the entry sets `optional = true`. Prefer explicit lists.

## Deliberately not used

- **`[secrets.fnox]` and task `secrets = [...]`**, added in mise 2026.10.4, are experimental and require `experimental = true` in the committed config. The stack uses the stable `fnox exec` wrapper instead. Revisit when the feature leaves experimental status.
- **`[deps]` (`mise deps`)** is experimental. `setup` installs dependencies explicitly.
- **The `mise-env-fnox` plugin and `_.fnox-env`** are deprecated. They put every secret into every task's environment.
- **Idiomatic version files** (`idiomatic_version_file_enable_tools`): versions live in `mise.toml` only.
