package installer

import (
	"strings"
	"testing"
)

func TestMarkdownConversion(t *testing.T) {
	tests := []struct{ name, input, claude, codex string }{
		{"mixed", "Use $demo and /other.", "Use /demo and /other.", "Use $demo and $other."},
		{"inline", "Try `$demo` or `/other`.", "Try `/demo` or `/other`.", "Try `$demo` or `$other`."},
		{"text fence", "```text\nUse $demo or /other\n```\n", "```text\nUse /demo or /other\n```\n", "```text\nUse $demo or $other\n```\n"},
		{"bare fence", "~~~\n$demo /other\n~~~", "~~~\n/demo /other\n~~~", "~~~\n$demo $other\n~~~"},
		{"links", "[$demo](/other) and [/other](https://a/$demo)", "[/demo](/other) and [/other](https://a/$demo)", "[$demo](/other) and [$other](https://a/$demo)"},
		{"multiline link", "[$demo](\n/other\n)", "[/demo](\n/other\n)", "[$demo](\n/other\n)"},
		{"path", "Read ~/.claude/skills/demo/SKILL.md and `${HOME}/.codex/skills/other`.", "Read /custom skills/demo/SKILL.md and `/custom skills/other`.", "Read /custom skills/demo/SKILL.md and `/custom skills/other`."},
		{"home path", "$HOME/.codex/skills/demo ~/.codex/skills/unknown", "/custom skills/demo ~/.codex/skills/unknown", "/custom skills/demo ~/.codex/skills/unknown"},
		{"prose around code", "$demo `echo /other` /other", "/demo `echo /other` /other", "$demo `echo /other` $other"},
	}
	for _, tt := range tests {
		for _, tool := range []string{"claude", "codex"} {
			t.Run(tt.name+"/"+tool, func(t *testing.T) {
				c := conversion{tool: tool, dest: "/custom skills", names: map[string]bool{"demo": true, "other": true}}
				want := tt.claude
				if tool == "codex" {
					want = tt.codex
				}
				got := c.markdown(tt.input)
				if got != want {
					t.Fatalf("got %q\nwant %q", got, want)
				}
				if again := c.markdown(got); again != got {
					t.Errorf("second conversion changed %q to %q", got, again)
				}
			})
		}
	}
}

func TestMarkdownPreserved(t *testing.T) {
	examples := []string{
		"> ```sh\n> $demo /other\n> ```",
		"- ```sh\n  $demo /other\n  ```",
		"1. ```sh\n   $demo /other\n   ```",
		"https://example.com/demo https://example.com/$demo?q=/other",
		"<https://example.com/$demo> <mailto:/demo>",
		"[link](/demo) [link](../$demo/a) [link](foo(bar/$demo))",
		"[ref]: /demo \"$demo\"\n[another]: https://a/$demo",
		"`echo $demo` `cat ~/.codex/skills/demo/SKILL.md`",
		"``echo `$demo` /other``",
		"`multiline\n/demo\nexample`",
		"```sh\n$demo /other\n~/.codex/skills/demo\n```",
		"~~~python\n$demo /other\n~~~",
		"````bash\n```\n$demo\n````",
		"    $demo /other\n\t$demo /other",
		"\\$demo \\/demo \\~/.codex/skills/demo",
		"$HOME ${HOME} $DEMO ${demo} $demo_var $demo-other $demo2 $democracy",
		"/demo-extra /demo2 /demo_file /demo/file /demo.md /demo../other",
		"~/demo ./demo ../demo /tmp/demo path/demo C:/demo foo$demo",
		"Use /unknown and $unknown or /help.",
		"~/.codex/skills/demo-more ~/.codex/skills/demo_var",
		"Use Codex with Claude Code and Claude.",
		"!`echo $demo`",
	}
	for _, input := range examples {
		for _, tool := range []string{"claude", "codex"} {
			t.Run(tool+"/"+strings.ReplaceAll(input, "\n", " "), func(t *testing.T) {
				c := conversion{tool: tool, dest: "/dest", names: map[string]bool{"demo": true, "other": true}}
				if got := c.markdown(input); got != input {
					t.Errorf("changed protected content\ngot  %q\nwant %q", got, input)
				}
			})
		}
	}
}
