package installer

import (
	"regexp"
	"strings"

	"github.com/maltehedderich/core-skills/cli/internal/source"
	"go.yaml.in/yaml/v3"
)

var descriptionWordingRE = regexp.MustCompile(`\bUse when (?:Claude Code|Claude|Codex)\b`)
var claudeSubstitutionRE = regexp.MustCompile(`\$\{CLAUDE_[A-Z0-9_]+\}|\$CLAUDE_[A-Z0-9_]+`)
var argumentPlaceholderRE = regexp.MustCompile(`\$ARGUMENTS\b|\$[0-9]+\b`)

func (c *conversion) description(fm *yaml.Node) bool {
	desc := source.Field(fm, "description")
	if desc == nil {
		return false
	}
	if desc.Kind != yaml.ScalarNode || desc.Tag != "!!str" {
		c.warn("description", "expected a string; repair the description before converting it")
		return false
	}
	value := descriptionWordingRE.ReplaceAllString(desc.Value, "Use when the assistant")
	if value != desc.Value {
		c.record("description wording")
	}
	value = c.markdown(value)
	if value == desc.Value {
		return false
	}
	desc.Value = value
	return true
}

func (c *conversion) boolean(n *yaml.Node, field string) (bool, bool) {
	if n == nil {
		return false, true
	}
	if n.Kind != yaml.ScalarNode || n.Tag != "!!bool" {
		c.warn(field, "expected a YAML boolean; set true or false manually to enable invocation-policy conversion")
		return false, false
	}
	var value bool
	if err := n.Decode(&value); err != nil {
		c.warn(field, "invalid boolean; set true or false manually")
		return false, false
	}
	return value, true
}

func (c *conversion) metadata(fm, optional *yaml.Node, optionalValid bool) (bool, bool) {
	c.file = "SKILL.md"
	fmChanged := c.description(fm)
	if c.tool == "codex" {
		for _, field := range []string{"allowed-tools", "disallowed-tools", "tools", "context", "agent", "model", "hooks", "when_to_use", "argument-hint", "user-invocable", "arguments", "hidden"} {
			if source.Field(fm, field) != nil {
				c.warn(field, "Claude-specific setting preserved; configure equivalent behavior manually in Codex")
			}
		}
	}
	disable := source.Field(fm, "disable-model-invocation")
	disabled, disableValid := c.boolean(disable, "disable-model-invocation")
	c.file = "agents/openai.yaml"
	policy := source.Field(optional, "policy")
	policyValid := optionalValid
	if policy != nil && policy.Kind != yaml.MappingNode {
		c.warn("policy", "expected a mapping; repair policy before converting invocation settings")
		policyValid = false
	}
	allow := source.Field(policy, "allow_implicit_invocation")
	allowed, allowValid := c.boolean(allow, "policy.allow_implicit_invocation")
	if c.tool == "claude" {
		if dependencies := source.Field(optional, "dependencies"); source.Field(dependencies, "tools") != nil {
			c.warn("dependencies.tools", "Codex tool dependencies are preserved; install and configure these tools manually in Claude")
		}
	}
	optionalChanged := false
	if c.tool == "codex" && optionalValid {
		iface := source.Field(optional, "interface")
		if iface != nil && iface.Kind != yaml.MappingNode {
			c.warn("interface", "expected a mapping; repair interface to convert default_prompt")
		} else {
			prompt := source.Field(iface, "default_prompt")
			if prompt != nil {
				if prompt.Kind != yaml.ScalarNode || prompt.Tag != "!!str" {
					c.warn("interface.default_prompt", "expected a string; repair the prompt to convert invocations")
				} else {
					value := c.markdown(prompt.Value)
					if value != prompt.Value {
						prompt.Value = value
						optionalChanged = true
					}
				}
			}
		}
	}
	if !disableValid || !allowValid || !policyValid {
		return fmChanged, optionalChanged
	}
	if disable != nil && allow != nil {
		if disabled == allowed {
			if c.tool == "claude" {
				c.file = "SKILL.md"
			}
			c.warn("invocation policy conflict", "disable-model-invocation and policy.allow_implicit_invocation disagree; explicit "+c.tool+" setting wins; reconcile the source settings manually")
		}
		return fmChanged, optionalChanged
	}
	if c.tool == "codex" && disable != nil && allow == nil {
		if optional != nil {
			if policy == nil {
				policy = newMapping()
				setField(optional, "policy", policy)
			}
			setField(policy, "allow_implicit_invocation", boolNode(!disabled))
		}
		c.record("automatic invocation policy")
		optionalChanged = true
	}
	if c.tool == "claude" && allow != nil && disable == nil {
		c.file = "SKILL.md"
		setField(fm, "disable-model-invocation", boolNode(!allowed))
		c.record("automatic invocation policy")
		fmChanged = true
	}
	return fmChanged, optionalChanged
}

func (c *conversion) unsupportedText(text string) {
	if c.tool != "codex" {
		return
	}
	if argumentPlaceholderRE.MatchString(text) {
		c.warn("argument placeholders", "Claude argument substitution is preserved; replace placeholders with explicit input instructions for Codex")
	}
	if claudeSubstitutionRE.MatchString(text) {
		c.warn("CLAUDE substitutions", "Claude runtime substitutions are preserved; supply equivalent values manually in Codex")
	}
	if strings.Contains(text, "!`") {
		c.warn("command injection", "Claude command injection is preserved; replace it with explicit execution instructions for Codex")
	}
}
