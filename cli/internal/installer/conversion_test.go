package installer

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/maltehedderich/core-skills/cli/internal/fsutil"
	"github.com/maltehedderich/core-skills/cli/internal/source"
)

func fixtureSkill(t *testing.T, files map[string]string) source.Skill {
	t.Helper()
	dir := t.TempDir()
	for path, content := range files {
		full := filepath.Join(dir, path)
		if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(full, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return source.Skill{Name: "demo", Dir: dir}
}

func TestMetadataConversion(t *testing.T) {
	tests := []struct{ name, tool, fm, optional, wantFM, wantOptional, warning string }{
		{name: "disable true", tool: "codex", fm: "disable-model-invocation: true", wantOptional: "allow_implicit_invocation: false"},
		{name: "disable false", tool: "codex", fm: "disable-model-invocation: false", wantOptional: "allow_implicit_invocation: true"},
		{name: "disable uppercase", tool: "codex", fm: "disable-model-invocation: TRUE", wantOptional: "allow_implicit_invocation: false"},
		{name: "allow true", tool: "claude", optional: "policy:\n  allow_implicit_invocation: true\n", wantFM: "disable-model-invocation: false"},
		{name: "allow false", tool: "claude", optional: "policy:\n  allow_implicit_invocation: false\n", wantFM: "disable-model-invocation: true"},
		{name: "existing fields", tool: "codex", fm: "disable-model-invocation: true", optional: "# presentation\ninterface:\n  display_name: Demo # keep\npolicy:\n  custom: keep\n", wantOptional: "allow_implicit_invocation: false"},
		{name: "conflict codex", tool: "codex", fm: "disable-model-invocation: true", optional: "policy:\n  allow_implicit_invocation: true\n", wantOptional: "allow_implicit_invocation: true", warning: "invocation policy conflict"},
		{name: "conflict claude", tool: "claude", fm: "disable-model-invocation: false", optional: "policy:\n  allow_implicit_invocation: false\n", wantFM: "disable-model-invocation: false", warning: "invocation policy conflict"},
		{name: "agreement", tool: "claude", fm: "disable-model-invocation: false", optional: "policy:\n  allow_implicit_invocation: true\n", wantFM: "disable-model-invocation: false"},
		{name: "invalid source", tool: "codex", fm: "disable-model-invocation: 'true'", warning: "disable-model-invocation"},
		{name: "invalid target", tool: "claude", fm: "disable-model-invocation: [true]", optional: "policy:\n  allow_implicit_invocation: false\n", warning: "disable-model-invocation"},
		{name: "invalid allow", tool: "codex", fm: "disable-model-invocation: true", optional: "policy:\n  allow_implicit_invocation: 'false'\n", warning: "policy.allow_implicit_invocation"},
		{name: "malformed optional", tool: "codex", fm: "disable-model-invocation: true", optional: "interface: [\n", warning: "YAML"},
		{name: "invalid policy", tool: "codex", fm: "disable-model-invocation: true", optional: "policy: false\n", warning: "policy"},
		{name: "empty optional", tool: "codex", fm: "disable-model-invocation: true", optional: "# empty\n", warning: "YAML"},
		{name: "multiple documents", tool: "codex", fm: "disable-model-invocation: true", optional: "policy: {}\n---\ninterface: {}\n", warning: "YAML"},
		{name: "dependency", tool: "claude", optional: "dependencies:\n  tools:\n    - type: mcp\n      value: docs\n", warning: "dependencies.tools"},
		{name: "prompt codex", tool: "codex", optional: "interface:\n  default_prompt: Use /demo and $other.\n", wantOptional: "Use $demo and $other."},
		{name: "prompt claude", tool: "claude", optional: "interface:\n  default_prompt: Use $demo.\n", wantOptional: "Use $demo."},
		{name: "invalid prompt", tool: "codex", optional: "interface:\n  default_prompt: [demo]\n", warning: "interface.default_prompt"},
		{name: "absent policies", tool: "codex"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			original := "---\nname: demo\ndescription: Sample\n" + tt.fm + "\n---\n\nBody unchanged.\r\n"
			files := map[string]string{"SKILL.md": original}
			if tt.optional != "" {
				files["agents/openai.yaml"] = tt.optional
			}
			skill := fixtureSkill(t, files)
			p, err := prepareSkill(skill, "/dest", []string{"other"}, tt.tool)
			if err != nil {
				t.Fatal(err)
			}
			gotFM, gotOptional := string(p.files["SKILL.md"]), string(p.files["agents/openai.yaml"])
			if !strings.Contains(gotFM, tt.wantFM) || !strings.Contains(gotOptional, tt.wantOptional) {
				t.Fatalf("unexpected metadata:\n%s\n%s", gotFM, gotOptional)
			}
			if !strings.HasSuffix(gotFM, "\nBody unchanged.\r\n") {
				t.Errorf("body changed: %q", gotFM)
			}
			if tt.warning != "" {
				found := false
				for _, w := range p.result.Warnings {
					if w.Rule == tt.warning {
						found = true
					}
					if w.File == "" || w.Message == "" {
						t.Errorf("incomplete warning: %+v", w)
					}
				}
				if !found {
					t.Errorf("missing %s warning: %+v", tt.warning, p.result.Warnings)
				}
			} else if len(p.result.Warnings) != 0 {
				t.Errorf("unexpected warnings: %+v", p.result.Warnings)
			}
			if tt.wantFM == "" && gotFM != original {
				t.Errorf("unmodified frontmatter changed: %s", gotFM)
			}
			if tt.wantOptional == "" && gotOptional != tt.optional {
				t.Errorf("unmodified optional metadata changed: %s", gotOptional)
			}
			if tt.name == "existing fields" {
				for _, want := range []string{"# presentation", "# keep", "custom: keep"} {
					if !strings.Contains(gotOptional, want) {
						t.Errorf("lost %s", want)
					}
				}
			}
			// Round-trip converted output through preparation to prove idempotence.
			secondFiles := map[string]string{}
			for path, data := range p.files {
				secondFiles[path] = string(data)
			}
			second, err := prepareSkill(fixtureSkill(t, secondFiles), "/dest", []string{"other"}, tt.tool)
			if err != nil {
				t.Fatal(err)
			}
			for path, data := range p.files {
				if !bytes.Equal(data, second.files[path]) {
					t.Errorf("second conversion changed %s", path)
				}
			}
			if len(second.result.Conversions) != 0 {
				t.Errorf("second conversion reports changes: %+v", second.result.Conversions)
			}
		})
	}
}

func TestDescriptionAndUnsupportedFeatures(t *testing.T) {
	skill := fixtureSkill(t, map[string]string{"SKILL.md": "---\n# keep comment\nname: alias\ndescription: >-\n  Use when Claude Code needs /other.\n  Codex and Claude are products.\ncustom:\n  nested: keep\nallowed-tools: Read\ncontext: fork\nagent: Explore\nmodel: inherit\nhooks: {}\nwhen_to_use: /other\nuser-invocable: false\nargument-hint: '[topic]'\narguments: [topic]\n---\nUse /alias. $ARGUMENTS $1 ${CLAUDE_SESSION_ID} !`echo /other`\n"})
	p, err := prepareSkill(skill, "/dest", []string{"other"}, "codex")
	if err != nil {
		t.Fatal(err)
	}
	got := string(p.files["SKILL.md"])
	for _, want := range []string{"Use when the assistant needs $other.", "Codex and Claude are products.", "# keep comment", "nested: keep", "Use $alias.", "!`echo /other`"} {
		if !strings.Contains(got, want) {
			t.Errorf("missing %q in %s", want, got)
		}
	}
	for _, rule := range []string{"allowed-tools", "context", "agent", "model", "hooks", "when_to_use", "user-invocable", "argument-hint", "arguments", "argument placeholders", "CLAUDE substitutions", "command injection"} {
		found := false
		for _, w := range p.result.Warnings {
			if w.Rule == rule {
				found = true
			}
		}
		if !found {
			t.Errorf("missing warning %s", rule)
		}
	}
}

func TestPreparationPreservesFilesAndSource(t *testing.T) {
	files := map[string]string{
		"SKILL.md":  "---\ndescription: Use when Codex needs a skill.\n---\nUse $demo and $other.",
		"README.md": "Use $other.", "references/more.md": "Use $demo.",
		"scripts/run.sh": "echo $demo", "scripts/README.md": "$demo", "templates/template.md": "$demo", "image.bin": "\x00$demo", "fake.md": "\x00$demo",
	}
	skill := fixtureSkill(t, files)
	dest := filepath.Join(t.TempDir(), "target")
	opts := Options{Options: fsutil.Options{DryRun: true}, KnownSkillNames: []string{"other"}}
	result, err := (&Claude{}).InstallSkill(skill, dest, opts)
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Conversions) == 0 {
		t.Fatal("no conversions")
	}
	if _, err := os.Stat(dest); !os.IsNotExist(err) {
		t.Fatalf("dry-run created destination: %v", err)
	}
	opts.DryRun = false
	if _, err := (&Claude{}).InstallSkill(skill, dest, opts); err != nil {
		t.Fatal(err)
	}
	again, err := (&Claude{}).InstallSkill(skill, dest, opts)
	if err != nil {
		t.Fatal(err)
	}
	if len(again.Written) != 0 || len(again.Skipped) != len(files) {
		t.Errorf("reinstall didn't skip: %+v", again)
	}
	for path, original := range files {
		data, err := os.ReadFile(filepath.Join(skill.Dir, path))
		if err != nil {
			t.Fatal(err)
		}
		if string(data) != original {
			t.Errorf("source changed: %s", path)
		}
		if strings.HasPrefix(path, "scripts/") || strings.HasPrefix(path, "templates/") || strings.Contains(original, "\x00") {
			got, err := os.ReadFile(filepath.Join(dest, skill.Name, path))
			if err != nil {
				t.Fatal(err)
			}
			if string(got) != original {
				t.Errorf("protected file changed: %s", path)
			}
		}
	}
}

func TestGeneratedMetadataConflictHandling(t *testing.T) {
	for _, mode := range []string{"force", "skip", "interactive", "abort"} {
		t.Run(mode, func(t *testing.T) {
			skill := fixtureSkill(t, map[string]string{"SKILL.md": "---\ndescription: Sample\ndisable-model-invocation: true\n---\n"})
			dest := t.TempDir()
			path := filepath.Join(dest, "demo", "agents", "openai.yaml")
			if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(path, []byte("old"), 0o644); err != nil {
				t.Fatal(err)
			}
			opts := Options{}
			called := false
			switch mode {
			case "force":
				opts.Force = true
			case "skip":
				opts.NoClobber = true
			default:
				opts.OnConflict = func(_ string, existing, incoming []byte) Action {
					called = true
					if string(existing) != "old" || !bytes.Contains(incoming, []byte("allow_implicit_invocation: false")) {
						t.Error("wrong conflict bytes")
					}
					if mode == "abort" {
						return ActionAbort
					}
					return ActionOverwrite
				}
			}
			_, err := (&Codex{}).InstallSkill(skill, dest, opts)
			if mode == "abort" {
				if err == nil {
					t.Fatal("expected abort")
				}
			} else if err != nil {
				t.Fatal(err)
			}
			data, err := os.ReadFile(path)
			if err != nil {
				t.Fatal(err)
			}
			if mode == "skip" || mode == "abort" {
				if string(data) != "old" {
					t.Error("overwrote existing metadata")
				}
			} else if !bytes.Contains(data, []byte("allow_implicit_invocation: false")) {
				t.Error("missing generated policy")
			}
			if (mode == "interactive" || mode == "abort") && !called {
				t.Error("missing conflict callback")
			}
		})
	}
}

func TestInvalidRequiredMetadataWritesNothing(t *testing.T) {
	for _, raw := range []string{"hi", "---\ndescription: [bad]\n---\n", "---\ndescription: ok\ndescription: duplicate\n---\n", "---\ndescription: [\n---\n"} {
		skill := fixtureSkill(t, map[string]string{"SKILL.md": raw, "README.md": "/demo"})
		dest := filepath.Join(t.TempDir(), "out")
		if _, err := (&Codex{}).InstallSkill(skill, dest, Options{}); err == nil {
			t.Errorf("accepted %q", raw)
		}
		if _, err := os.Stat(dest); !os.IsNotExist(err) {
			t.Errorf("wrote before validation: %v", err)
		}
	}
}

func TestGoogleKeywordSkillRegression(t *testing.T) {
	dir := filepath.Join("..", "..", "..", "skills", "google-keyword-research")
	for _, inst := range []Installer{&Claude{}, &Codex{}, &Copilot{}, &Gemini{}} {
		t.Run(inst.Name(), func(t *testing.T) {
			dest := t.TempDir()
			skill := source.Skill{Name: "google-keyword-research", Dir: dir}
			if _, err := inst.InstallSkill(skill, dest, Options{}); err != nil {
				t.Fatal(err)
			}
			for _, path := range []string{"README.md", "agents/openai.yaml", "scripts/google_keywords.py"} {
				original, err := os.ReadFile(filepath.Join(dir, path))
				if err != nil {
					t.Fatal(err)
				}
				got, err := os.ReadFile(filepath.Join(dest, skill.Name, path))
				if err != nil {
					t.Fatal(err)
				}
				want := string(original)
				if inst.Name() == "claude" && path == "README.md" {
					want = strings.ReplaceAll(want, "$google-keyword-research", "/google-keyword-research")
				}
				if string(got) != want {
					t.Errorf("unexpected change in %s", path)
				}
			}
		})
	}
}

func TestInstalledPaths(t *testing.T) {
	for _, inst := range []Installer{&Claude{}, &Codex{}} {
		for _, dest := range []string{inst.DefaultDir(KindSkill), "/custom skills"} {
			for _, prefix := range []string{"~", "$HOME", "${HOME}"} {
				c := conversion{tool: inst.Name(), dest: dest, names: map[string]bool{"demo": true}}
				input := "Read " + prefix + "/.claude/skills/demo/SKILL.md and `" + prefix + "/.codex/skills/demo`."
				want := "Read " + filepath.ToSlash(filepath.Join(dest, "demo", "SKILL.md")) + " and `" + filepath.ToSlash(filepath.Join(dest, "demo")) + "`."
				if got := c.markdown(input); got != want {
					t.Errorf("got %q; want %q", got, want)
				}
			}
		}
	}
}

func TestArgumentNameCollision(t *testing.T) {
	skill := fixtureSkill(t, map[string]string{"SKILL.md": "---\ndescription: Sample\narguments: [other]\n---\nUse $other as an argument and /other as a skill.\n"})
	for _, tool := range []string{"claude", "codex"} {
		p, err := prepareSkill(skill, "/dest", []string{"other"}, tool)
		if err != nil {
			t.Fatal(err)
		}
		if !strings.Contains(string(p.files["SKILL.md"]), "Use $other as an argument") {
			t.Errorf("rewrote argument for %s", tool)
		}
	}
}
