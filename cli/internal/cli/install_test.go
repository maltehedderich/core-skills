package cli

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// fixtureRepo points at the source-package fixture clone so the CLI tests
// don't drift from the loader tests.
func fixtureRepo(t *testing.T) string {
	t.Helper()
	wd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	// internal/cli -> internal/source/testdata/fixture-repo
	repo := filepath.Join(wd, "..", "source", "testdata", "fixture-repo")
	abs, err := filepath.Abs(repo)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(abs, "agents")); err != nil {
		t.Fatalf("fixture repo missing: %v", err)
	}
	return abs
}

func runCLI(t *testing.T, args ...string) (int, string, string) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run(args, nil, &stdout, &stderr)
	return code, stdout.String(), stderr.String()
}

func TestInstallCopilotSingleAgent(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, errOut := runCLI(t,
		"install",
		"--tool", "copilot",
		"--agents", "sample-agent",
		"--repo", repo,
		"--dest", dest,
	)
	if code != 0 {
		t.Fatalf("exit = %d, want 0; stderr:\n%s", code, errOut)
	}
	want := filepath.Join(dest, "sample-agent.agent.md")
	if _, err := os.Stat(want); err != nil {
		t.Fatalf("expected %s to exist: %v", want, err)
	}
}

func TestInstallAllAgents(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, errOut := runCLI(t,
		"install",
		"--tool", "copilot",
		"--agents", "all",
		"--repo", repo,
		"--dest", dest,
	)
	if code != 0 {
		t.Fatalf("exit = %d, want 0; stderr:\n%s", code, errOut)
	}
	if _, err := os.Stat(filepath.Join(dest, "sample-agent.agent.md")); err != nil {
		t.Fatalf("missing installed agent: %v", err)
	}
}

func TestInstallClaudeRewritesName(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, _ := runCLI(t,
		"install",
		"--tool", "claude",
		"--agents", "sample-agent",
		"--repo", repo,
		"--dest", dest,
	)
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	got, err := os.ReadFile(filepath.Join(dest, "sample-agent.agent.md"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(got), `name: "core-skills:sample-agent"`) {
		t.Errorf("missing namespaced name; got:\n%s", got)
	}
}

func TestInstallCodexAgentEmitsNativeAgentFile(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, _ := runCLI(t,
		"install",
		"--tool", "codex",
		"--agents", "sample-agent",
		"--repo", repo,
		"--dest", dest,
	)
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	target := filepath.Join(dest, "sample-agent.toml")
	if _, err := os.Stat(target); err != nil {
		t.Fatalf("missing native Codex agent file: %v", err)
	}
}

func TestInstallSkill(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, _ := runCLI(t,
		"install",
		"--tool", "copilot",
		"--skills", "sample-skill",
		"--repo", repo,
		"--dest", dest,
	)
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if _, err := os.Stat(filepath.Join(dest, "sample-skill", "SKILL.md")); err != nil {
		t.Fatalf("missing skill: %v", err)
	}
}

func TestInstallNoClobberLeavesExistingDifferingFile(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()
	existing := filepath.Join(dest, "sample-agent.agent.md")
	if err := os.WriteFile(existing, []byte("old content"), 0o644); err != nil {
		t.Fatal(err)
	}

	code, _, _ := runCLI(t,
		"install",
		"--tool", "copilot",
		"--agents", "sample-agent",
		"--repo", repo,
		"--dest", dest,
		"--no-clobber",
	)
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	got, _ := os.ReadFile(existing)
	if string(got) != "old content" {
		t.Errorf("file changed despite --no-clobber: %q", got)
	}
}

func TestInstallForceOverwrites(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()
	existing := filepath.Join(dest, "sample-agent.agent.md")
	if err := os.WriteFile(existing, []byte("old"), 0o644); err != nil {
		t.Fatal(err)
	}

	code, _, _ := runCLI(t,
		"install",
		"--tool", "copilot",
		"--agents", "sample-agent",
		"--repo", repo,
		"--dest", dest,
		"--force",
	)
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	got, _ := os.ReadFile(existing)
	if string(got) == "old" {
		t.Error("file was not overwritten")
	}
}

func TestInstallDryRunWritesNothing(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, out, _ := runCLI(t,
		"install",
		"--tool", "copilot",
		"--agents", "sample-agent",
		"--repo", repo,
		"--dest", dest,
		"--dry-run",
	)
	if code != 0 {
		t.Fatalf("exit = %d", code)
	}
	if _, err := os.Stat(filepath.Join(dest, "sample-agent.agent.md")); !os.IsNotExist(err) {
		t.Errorf("dry-run wrote file; stat err = %v", err)
	}
	if !strings.Contains(out, "dry-run") && !strings.Contains(out, "would") {
		t.Errorf("dry-run output should announce itself; got:\n%s", out)
	}
}

func TestInstallUnknownToolExits2(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, errOut := runCLI(t,
		"install",
		"--tool", "bogus",
		"--agents", "sample-agent",
		"--repo", repo,
		"--dest", dest,
	)
	if code != 2 {
		t.Errorf("exit = %d, want 2", code)
	}
	if !strings.Contains(errOut, "bogus") {
		t.Errorf("stderr should mention bogus tool: %q", errOut)
	}
}

func TestInstallUnknownAgentExits2(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, errOut := runCLI(t,
		"install",
		"--tool", "copilot",
		"--agents", "does-not-exist",
		"--repo", repo,
		"--dest", dest,
	)
	if code != 2 {
		t.Errorf("exit = %d, want 2", code)
	}
	if !strings.Contains(errOut, "does-not-exist") {
		t.Errorf("stderr should name the unknown agent: %q", errOut)
	}
}

func TestInstallNoTTYNoToolExits2(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, errOut := runCLI(t,
		"install",
		"--repo", repo,
		"--dest", dest,
	)
	if code != 2 {
		t.Errorf("exit = %d, want 2", code)
	}
	if !strings.Contains(strings.ToLower(errOut), "tool") {
		t.Errorf("stderr should ask for --tool: %q", errOut)
	}
}

func TestInstallForceAndNoClobberConflict(t *testing.T) {
	repo := fixtureRepo(t)
	dest := t.TempDir()

	code, _, errOut := runCLI(t,
		"install",
		"--tool", "copilot",
		"--agents", "sample-agent",
		"--repo", repo,
		"--dest", dest,
		"--force",
		"--no-clobber",
	)
	if code != 2 {
		t.Errorf("exit = %d, want 2", code)
	}
	if !strings.Contains(strings.ToLower(errOut), "force") {
		t.Errorf("stderr should explain mutex; got: %q", errOut)
	}
}

func TestSkillConversionCLI(t *testing.T) {
	repo := t.TempDir()
	files := map[string]string{
		"skills/first/SKILL.md":  "---\nname: first\ndescription: Use when Codex needs help.\ndisable-model-invocation: true\ncontext: fork\n---\nUse /second-alias or $second-alias.\n",
		"skills/second/SKILL.md": "---\nname: second-alias\ndescription: Second skill\n---\n",
	}
	for path, raw := range files {
		full := filepath.Join(repo, path)
		if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(full, []byte(raw), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	for _, tool := range []string{"codex", "claude", "copilot", "gemini"} {
		t.Run(tool, func(t *testing.T) {
			dest := filepath.Join(t.TempDir(), "destination with spaces")
			args := []string{"install", "--repo", repo, "--tool", tool, "--skills", "first", "--dest", dest}
			code, out, errOut := runCLI(t, append(args, "--dry-run", "--verbose")...)
			if code != 0 {
				t.Fatalf("dry-run failed: %s", errOut)
			}
			if _, err := os.Stat(dest); !os.IsNotExist(err) {
				t.Fatal("dry-run wrote files")
			}
			if tool == "codex" && (!strings.Contains(errOut, "context") || !strings.Contains(out, "automatic invocation policy")) {
				t.Errorf("missing diagnostics: %s / %s", out, errOut)
			}
			code, normal, normalErr := runCLI(t, args...)
			if code != 0 {
				t.Fatalf("install failed: %s", normalErr)
			}
			if normalErr != errOut {
				t.Errorf("dry-run warnings differ: %s / %s", errOut, normalErr)
			}
			if !strings.Contains(normal, "conversion(s) prepared") {
				t.Error("missing conversion count")
			}
			got, err := os.ReadFile(filepath.Join(dest, "first", "SKILL.md"))
			if err != nil {
				t.Fatal(err)
			}
			want := files["skills/first/SKILL.md"]
			switch tool {
			case "codex":
				if !strings.Contains(string(got), "Use $second-alias or $second-alias.") {
					t.Errorf("missing full catalog alias: %s", got)
				}
			case "claude":
				if !strings.Contains(string(got), "Use /second-alias or /second-alias.") {
					t.Errorf("missing full catalog alias: %s", got)
				}
			default:
				if string(got) != want {
					t.Error("non-target tool changed bytes")
				}
			}
			if _, err := os.Stat(filepath.Join(dest, "second")); !os.IsNotExist(err) {
				t.Error("installed unselected skill")
			}
			code, repeat, repeatErr := runCLI(t, args...)
			if code != 0 {
				t.Fatal(repeatErr)
			}
			if !strings.Contains(repeat, "0 file(s) written") {
				t.Errorf("repeat install wrote files: %s", repeat)
			}
			target := filepath.Join(dest, "first", "SKILL.md")
			if err := os.WriteFile(target, []byte("local edit"), 0o644); err != nil {
				t.Fatal(err)
			}
			code, _, skipErr := runCLI(t, append(args, "--no-clobber")...)
			if code != 0 {
				t.Fatal(skipErr)
			}
			data, err := os.ReadFile(target)
			if err != nil {
				t.Fatal(err)
			}
			if string(data) != "local edit" {
				t.Error("no-clobber overwrote file")
			}
			code, _, forceErr := runCLI(t, append(args, "--force")...)
			if code != 0 {
				t.Fatal(forceErr)
			}
			data, err = os.ReadFile(target)
			if err != nil {
				t.Fatal(err)
			}
			if !bytes.Equal(data, got) {
				t.Error("force didn't restore converted output")
			}
		})
	}
	for path, want := range files {
		got, err := os.ReadFile(filepath.Join(repo, path))
		if err != nil {
			t.Fatal(err)
		}
		if string(got) != want {
			t.Errorf("source edited: %s", path)
		}
	}
}
