package source

import (
	"bytes"
	"fmt"
	"io"
	"regexp"
	"strings"

	"go.yaml.in/yaml/v3"
)

// SkillMarkdown retains the exact delimiters and body while exposing YAML nodes.
type SkillMarkdown struct {
	Metadata             *yaml.Node
	Prefix, Suffix, Body []byte
}

// ParseSkillMarkdown parses and validates the required skill description.
func ParseSkillMarkdown(raw []byte) (*SkillMarkdown, error) {
	first := bytes.IndexByte(raw, '\n')
	if first < 0 || strings.TrimSuffix(string(raw[:first]), "\r") != "---" {
		return nil, fmt.Errorf("file does not start with frontmatter delimiter '---'")
	}
	for start := first + 1; start < len(raw); {
		end := bytes.IndexByte(raw[start:], '\n')
		next := len(raw)
		if end < 0 {
			end = len(raw)
		} else {
			end += start
			next = end + 1
		}
		if strings.TrimSuffix(string(raw[start:end]), "\r") == "---" {
			doc, err := ParseMapping(raw[first+1 : start])
			if err != nil {
				return nil, err
			}
			desc := Field(doc, "description")
			if desc == nil || desc.Kind != yaml.ScalarNode || desc.Tag != "!!str" || strings.TrimSpace(desc.Value) == "" {
				return nil, fmt.Errorf("missing description or invalid description (expected non-empty string)")
			}
			return &SkillMarkdown{Metadata: doc, Prefix: raw[:first+1], Suffix: raw[start:next], Body: raw[next:]}, nil
		}
		start = next
	}
	return nil, fmt.Errorf("frontmatter not closed with '---'")
}

// ParseMapping parses one YAML mapping, retaining comments and unknown fields.
func ParseMapping(raw []byte) (*yaml.Node, error) {
	var doc yaml.Node
	dec := yaml.NewDecoder(bytes.NewReader(raw))
	if err := dec.Decode(&doc); err != nil {
		return nil, err
	}
	if len(doc.Content) != 1 || doc.Content[0].Kind != yaml.MappingNode {
		return nil, fmt.Errorf("expected YAML mapping")
	}
	// Decode once into a value to also reject duplicate keys.
	var check map[string]any
	if err := doc.Decode(&check); err != nil {
		return nil, err
	}
	var extra yaml.Node
	if err := dec.Decode(&extra); err != io.EOF {
		if err != nil {
			return nil, err
		}
		return nil, fmt.Errorf("expected a single YAML document")
	}
	return doc.Content[0], nil
}

// Field returns a direct mapping value, or nil when absent.
func Field(mapping *yaml.Node, key string) *yaml.Node {
	if mapping == nil || mapping.Kind != yaml.MappingNode {
		return nil
	}
	for i := 0; i+1 < len(mapping.Content); i += 2 {
		if mapping.Content[i].Value == key {
			return mapping.Content[i+1]
		}
	}
	return nil
}

var skillNameRE = regexp.MustCompile(`^[a-z0-9]+(-[a-z0-9]+)*$`)

// ValidSkillName identifies names usable as complete invocation tokens.
func ValidSkillName(name string) bool { return len(name) <= 64 && skillNameRE.MatchString(name) }

// SkillNames includes directory names and valid frontmatter aliases.
func SkillNames(skills []Skill) []string {
	var names []string
	for _, skill := range skills {
		names = append(names, skill.Name)
		if skill.InvocationName != "" && skill.InvocationName != skill.Name {
			names = append(names, skill.InvocationName)
		}
	}
	return names
}
