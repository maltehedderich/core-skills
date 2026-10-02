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
| [`google-keyword-research`](skills/google-keyword-research/README.md) | Discover and prioritize Google keywords using search volumes, monthly trends, advertiser competition, and bid ranges. |

After installation, invoke the skill by name. In Codex:

```text
Use $agentic-browsing-auditor to audit the current page or repository and improve its agentic browsing readiness.
```

In Claude Code:

```text
/agentic-browsing-auditor Audit the current page or repository and improve its agentic browsing readiness.
```

## Automatic Claude ↔ Codex Conversion

Installing with `--tool claude` or `--tool codex` normalizes the installed copy for that tool, regardless of which tool the source was written for. Source files stay unchanged. Copilot, Gemini, and agent installation keep their existing behavior.

| Content | Installed behavior |
| --- | --- |
| Skill invocations | `$skill-name` for Codex; `/skill-name` for Claude. Recognizes directory names and valid frontmatter names from the full source catalog, including unselected skills. |
| Installed paths | Explicit `~/.claude/skills/<known-skill>` and `~/.codex/skills/<known-skill>` references use the target destination, including `--dest`. `$HOME` and `${HOME}` prefixes also work. |
| Automatic invocation | Claude's `disable-model-invocation` maps to the inverse of Codex's `policy.allow_implicit_invocation` in `agents/openai.yaml`, and vice versa. Missing target metadata is created only when a source setting exists. |
| Descriptions | The phrases “Use when Codex”, “Use when Claude”, and “Use when Claude Code” become “Use when the assistant”. Other product mentions remain. |
| Codex default prompt | `interface.default_prompt` in `agents/openai.yaml` uses `$skill-name` for Codex. Claude installs preserve this Codex-specific prompt and presentation metadata. |

The invocation settings follow the [Claude skill reference](https://code.claude.com/docs/en/skills) and [Codex skill reference](https://learn.chatgpt.com/docs/build-skills). If both settings exist, the explicit target setting wins. Conflicts produce a warning, and the source setting is preserved.

Conversion covers Markdown instructions, READMEs, and references: prose, standalone inline invocations and paths, and unlabelled or `text` fenced examples. Executable fences, indented code, scripts, templates, binaries, URLs, and Markdown link destinations stay unchanged. Only complete, known invocation tokens are converted; unknown commands, escapes, variables, longer names, and path fragments are preserved. Skill names, general product names, and tool APIs are not translated. Commands are never executed during conversion.

Unsupported content is retained with compatibility warnings. Codex installs flag Claude execution settings, permissions, invocation hints, visibility, arguments, runtime substitutions, and command injection for manual adjustment. Claude installs flag Codex tool dependencies for manual setup. Malformed optional YAML or invalid conversion-field types produce warnings and skip the affected conversion; invalid required skill metadata fails installation. YAML comments and unknown fields are retained, and metadata is re-encoded only when changed.

Normal output counts prepared conversions as file/rule pairs; `--verbose` lists those files and rules. Warnings always go to stderr. `--dry-run` computes the same conversions and warnings without writing. All generated and changed files use the existing conflict handling, including `--force`, `--no-clobber`, and interactive prompts. Identical installed output is skipped on reinstall. A prepared conversion may be skipped when an existing file is kept.

## Work With the CLI

From the repository root, use GNU Make 3.81 or newer with a POSIX shell:

```sh
make                 # Show available targets
make cli-build       # Build cli/bin/dev/coreskills from local source
make test            # Run Go and keyword research Python tests
make check           # Run the CLI checks used in CI
```

`make check` requires Go, golangci-lint v2.11.4, and GoReleaser v2.15.4,
matching CI. It runs tests, vet, lint, and release configuration validation
without rewriting tracked files. `make test` also requires `uv`; its Python
test command may download the Google Ads SDK dependencies. Go commands may
download the toolchain and modules when they are not cached. Run `make cli-test`
or `make keywords-test` to test one component. The CLI build can be run directly
with `cli/bin/dev/coreskills list --repo .`.

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

`SKILL.md` must start with YAML frontmatter that includes `name` and `description`. The CLI discovers skills from `skills/<name>/SKILL.md` and installs the full skill folder, applying the conversions above for Claude and Codex.

Run this command to verify that the skill appears in the catalog:

```sh
./coreskills list
```

## Release

Tagged releases that match `v*` run GoReleaser from `cli/.goreleaser.yaml`. Release archives are named `coreskills_<os>_<arch>` and include the root `README.md` and `LICENSE`.

## License

Core Skills is licensed under the [MIT License](LICENSE).
