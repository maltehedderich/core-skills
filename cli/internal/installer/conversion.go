package installer

import (
	"bytes"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/maltehedderich/core-skills/cli/internal/source"
	"go.yaml.in/yaml/v3"
)

type conversion struct {
	tool, dest, file string
	names            map[string]bool
	result           Result
}

type preparedSkill struct {
	files  map[string][]byte
	dirs   []string
	result Result
}

func installConvertedSkill(skill source.Skill, dest string, opts Options, tool string) (Result, error) {
	prepared, err := prepareSkill(skill, dest, opts.KnownSkillNames, tool)
	if err != nil {
		return prepared.result, err
	}
	result := prepared.result
	for _, dir := range prepared.dirs {
		if !opts.DryRun {
			if err := os.MkdirAll(filepath.Join(dest, skill.Name, dir), 0o755); err != nil {
				return result, fmt.Errorf("mkdir %s: %w", dir, err)
			}
		}
	}
	paths := make([]string, 0, len(prepared.files))
	for path := range prepared.files {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	for _, path := range paths {
		one, err := writeOne(filepath.Join(dest, skill.Name, path), prepared.files[path], opts)
		result.Merge(one)
		if err != nil {
			return result, err
		}
	}
	return result, nil
}

func prepareSkill(skill source.Skill, dest string, names []string, tool string) (preparedSkill, error) {
	p := preparedSkill{files: make(map[string][]byte)}
	err := filepath.WalkDir(skill.Dir, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, err := filepath.Rel(skill.Dir, path)
		if err != nil {
			return err
		}
		if d.IsDir() {
			p.dirs = append(p.dirs, rel)
			return nil
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("read %s: %w", path, err)
		}
		p.files[filepath.ToSlash(rel)] = raw
		return nil
	})
	if err != nil {
		return p, err
	}
	md, err := source.ParseSkillMarkdown(p.files["SKILL.md"])
	if err != nil {
		return p, fmt.Errorf("parse %s/SKILL.md: %w", skill.Dir, err)
	}
	c := conversion{tool: tool, dest: dest, names: make(map[string]bool)}
	for _, name := range append(names, skill.Name, skill.InvocationName) {
		if source.ValidSkillName(name) {
			c.names[name] = true
		}
	}
	if name := source.Field(md.Metadata, "name"); name != nil && name.Tag == "!!str" && source.ValidSkillName(name.Value) {
		c.names[name.Value] = true
	}
	c.file = "SKILL.md"
	var optional *yaml.Node
	optionalValid := true
	if raw, ok := p.files["agents/openai.yaml"]; ok {
		optional, err = source.ParseMapping(raw)
		if err != nil {
			c.file = "agents/openai.yaml"
			c.warn("YAML", "malformed optional metadata; repair YAML to enable metadata conversion: "+err.Error())
			optionalValid = false
		}
	}
	fmChanged, optionalChanged := c.metadata(md.Metadata, optional, optionalValid)
	// metadata can create an optional document when the source policy requires it.
	if optional == nil && optionalChanged {
		optional = newMapping()
		policy := newMapping()
		setField(optional, "policy", policy)
		value := source.Field(md.Metadata, "disable-model-invocation")
		var disabled bool
		if err := value.Decode(&disabled); err != nil {
			return p, err
		}
		setField(policy, "allow_implicit_invocation", boolNode(!disabled))
	}
	if optionalChanged {
		raw, err := encodeMetadata(optional)
		if err != nil {
			return p, err
		}
		p.files["agents/openai.yaml"] = raw
	}
	paths := make([]string, 0, len(p.files))
	for path := range p.files {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	for _, path := range paths {
		c.file = path
		if !instructionFile(path) || bytes.ContainsRune(p.files[path], 0) {
			continue
		}
		raw := p.files[path]
		if path == "SKILL.md" {
			c.unsupportedText(string(raw))
			body := []byte(c.markdown(string(md.Body)))
			if fmChanged {
				metadata, err := encodeMetadata(md.Metadata)
				if err != nil {
					return p, err
				}
				p.files[path] = bytes.Join([][]byte{md.Prefix, metadata, md.Suffix, body}, nil)
			} else {
				p.files[path] = append(bytes.Clone(raw[:len(raw)-len(md.Body)]), body...)
			}
		} else {
			c.unsupportedText(string(raw))
			// Optional Markdown frontmatter is handled separately from its body.
			if bytes.HasPrefix(raw, []byte("---\n")) || bytes.HasPrefix(raw, []byte("---\r\n")) {
				other, err := source.ParseSkillMarkdown(raw)
				if err != nil {
					c.warn("YAML", "repair optional Markdown frontmatter to enable conversion: "+err.Error())
					continue
				}
				changed := c.description(other.Metadata)
				prefix := raw[:len(raw)-len(other.Body)]
				if changed {
					metadata, err := encodeMetadata(other.Metadata)
					if err != nil {
						return p, err
					}
					prefix = bytes.Join([][]byte{other.Prefix, metadata, other.Suffix}, nil)
				}
				p.files[path] = append(bytes.Clone(prefix), []byte(c.markdown(string(other.Body)))...)
			} else {
				p.files[path] = []byte(c.markdown(string(raw)))
			}
		}
	}
	// Qualify diagnostic paths with the source skill folder for multi-skill runs.
	for i := range c.result.Conversions {
		c.result.Conversions[i].File = filepath.Join(skill.Dir, c.result.Conversions[i].File)
	}
	for i := range c.result.Warnings {
		c.result.Warnings[i].File = filepath.Join(skill.Dir, c.result.Warnings[i].File)
	}
	p.result = c.result
	return p, nil
}

func instructionFile(path string) bool {
	for _, part := range strings.Split(path, "/") {
		switch strings.ToLower(part) {
		case "scripts", "templates", "assets", "node_modules", ".git":
			return false
		}
	}
	return strings.EqualFold(filepath.Ext(path), ".md") || strings.EqualFold(filepath.Ext(path), ".markdown") || strings.EqualFold(filepath.Base(path), "README")
}

func (c *conversion) record(rule string) {
	for _, d := range c.result.Conversions {
		if d.File == c.file && d.Rule == rule {
			return
		}
	}
	c.result.Conversions = append(c.result.Conversions, Diagnostic{File: c.file, Rule: rule})
}
func (c *conversion) warn(rule, message string) {
	c.result.Warnings = append(c.result.Warnings, Diagnostic{File: c.file, Rule: rule, Message: message})
}

func newMapping() *yaml.Node { return &yaml.Node{Kind: yaml.MappingNode, Tag: "!!map"} }
func setField(m *yaml.Node, key string, value *yaml.Node) {
	m.Content = append(m.Content, &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Value: key}, value)
}
func boolNode(value bool) *yaml.Node {
	return &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!bool", Value: fmt.Sprint(value)}
}
func encodeMetadata(m *yaml.Node) ([]byte, error) {
	var b bytes.Buffer
	enc := yaml.NewEncoder(&b)
	enc.SetIndent(2)
	if err := enc.Encode(m); err != nil {
		return nil, fmt.Errorf("encode skill metadata: %w", err)
	}
	if err := enc.Close(); err != nil {
		return nil, fmt.Errorf("close metadata encoder: %w", err)
	}
	return b.Bytes(), nil
}
