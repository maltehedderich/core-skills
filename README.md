# Core Skills

Core Skills is a catalog of reusable AI assistant skills, plus a CLI that installs them into Claude Code, Codex, GitHub Copilot, and Gemini.

Use it when you want the same specialized skill instructions available across tools without hand-copying folders into each tool's config directory.

## Install a Skill

Clone the repo, list the available artifacts, then install the skill you need:

```sh
git clone https://github.com/maltehedderich/core-skills.git
cd core-skills
./coreskills list
./coreskills install --tool codex --skills agentic-browsing-auditor
```

The `./coreskills` wrapper runs the CLI from this repo. It uses a cached binary when present, downloads the latest GitHub Release when available, and falls back to building the CLI with Go.

To preview writes before changing your local tool config, run:

```sh
./coreskills install --tool codex --skills agentic-browsing-auditor --dry-run --verbose
```

## Choose a Target Tool

Pass one of these values to `--tool`:

| Tool | Skill destination |
| --- | --- |
| `claude` | `~/.claude/skills/<skill-name>` |
| `codex` | `~/.codex/skills/<skill-name>` |
| `copilot` | `~/.copilot/skills/<skill-name>` |
| `gemini` | `~/.gemini/skills/<skill-name>` |

Use `--dest` to write into a different directory:

```sh
./coreskills install --tool codex --skills agentic-browsing-auditor --dest /tmp/codex-skills
```

Use `--force` to overwrite existing files without prompting, or `--no-clobber` to skip files that already exist.

## Available Skills

| Skill | Use it to |
| --- | --- |
| [`add-ask-ai-footer`](skills/add-ask-ai-footer/README.md) | Add AI assistant summary links to a website footer while matching existing styling and provider link behavior. |
| [`agentic-browsing-auditor`](skills/agentic-browsing-auditor/README.md) | Audit and improve a website, current page, or frontend repository for Lighthouse Agentic Browsing readiness. |

After installation, invoke the skill by name in your AI tool. For example:

```text
Use $agentic-browsing-auditor to audit the current page or repository and improve its agentic browsing readiness.
```

## Work With the CLI

The CLI source lives under `cli/`.

```sh
cd cli
go test ./...
go vet ./...
go run ./cmd/coreskills list --repo ..
```

The module currently targets the Go version declared in [`cli/go.mod`](cli/go.mod).

## Add a Skill

Create a folder under `skills/` with this shape:

```text
skills/<skill-name>/
  SKILL.md
  README.md
  references/
```

`SKILL.md` must start with YAML frontmatter that includes `name` and `description`. The CLI discovers skills from `skills/<name>/SKILL.md` and copies the full skill folder into the target tool.

Run this command to verify that the skill appears in the catalog:

```sh
./coreskills list
```

## Release

Tagged releases that match `v*` run GoReleaser from `cli/.goreleaser.yaml`. Release archives are named `coreskills_<os>_<arch>` and include the root `README.md` and `LICENSE`.

## License

Core Skills is licensed under the [MIT License](LICENSE).
