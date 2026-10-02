package source

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestSkillYAMLDiscovery(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, "skills", "folder")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	raw := "---\nname: invocation-name\ndescription: >-\n  First line with a colon: value.\n  Second line.\nmetadata:\n  nested: value\n---\nBody"
	if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte(raw), 0o644); err != nil {
		t.Fatal(err)
	}
	skills, err := (&Source{Root: root}).Skills()
	if err != nil {
		t.Fatal(err)
	}
	if len(skills) != 1 || skills[0].Description != "First line with a colon: value. Second line." {
		t.Fatalf("unexpected discovery: %+v", skills)
	}
	if got := SkillNames(skills); !reflect.DeepEqual(got, []string{"folder", "invocation-name"}) {
		t.Errorf("names = %v", got)
	}
}

func TestSkillMarkdownValidation(t *testing.T) {
	for _, raw := range []string{
		"", "---\ndescription: good", "---\nname: demo\n---\n",
		"---\ndescription: false\n---\n", "---\ndescription: []\n---\n",
		"---\ndescription: ''\n---\n", "---\ndescription: x\ndescription: y\n---\n",
	} {
		if _, err := ParseSkillMarkdown([]byte(raw)); err == nil {
			t.Errorf("accepted invalid metadata %q", raw)
		}
	}
	for _, raw := range []string{
		"---\ndescription: 'quoted: value'\n---\nBody",
		"---\r\ndescription: |\r\n  Multiline\r\n  description\r\n---\r\nBody\r\n",
	} {
		md, err := ParseSkillMarkdown([]byte(raw))
		if err != nil {
			t.Fatal(err)
		}
		if len(md.Body) == 0 {
			t.Fatal("missing body")
		}
	}
}
