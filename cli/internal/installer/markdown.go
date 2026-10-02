package installer

import (
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"unicode"
	"unicode/utf8"
)

var invocationRE = regexp.MustCompile(`[$/][a-z0-9][a-z0-9-]*`)
var installedPathRE = regexp.MustCompile(`(?:~|\$HOME|\$\{HOME\})/\.(?:claude|codex)/skills/([a-z0-9][a-z0-9-]*)`)
var urlRE = regexp.MustCompile(`(?:[a-zA-Z][a-zA-Z0-9+.-]*://|mailto:|www\.)[^\s<>]+`)
var referenceLinkRE = regexp.MustCompile(`^ {0,3}\[[^\]]+\]:`)

// markdown converts only prose and explicitly non-executable examples. Every
// protected span is copied from the input rather than rendered from an AST.
func (c *conversion) markdown(input string) string {
	lines := strings.SplitAfter(input, "\n")
	var out, prose strings.Builder
	flush := func() { out.WriteString(c.inline(prose.String())); prose.Reset() }
	var fence byte
	var fenceLen int
	var convertFence bool
	for _, line := range lines {
		trimmed := strings.TrimLeft(line, " ")
		indent := len(line) - len(trimmed)
		marker, count := fenceMarker(trimmed)
		if fence != 0 {
			if marker == fence && count >= fenceLen && strings.TrimSpace(trimmed[count:]) == "" {
				fence = 0
				out.WriteString(line)
			} else if convertFence {
				out.WriteString(c.inline(line))
			} else {
				out.WriteString(line)
			}
			continue
		}
		if indent <= 3 && count >= 3 {
			flush()
			fence, fenceLen = marker, count
			info := strings.TrimSpace(trimmed[count:])
			convertFence = info == "" || info == "text"
			out.WriteString(line)
			continue
		}
		if indent >= 4 || strings.HasPrefix(line, "\t") || referenceLinkRE.MatchString(line) {
			flush()
			out.WriteString(line)
			continue
		}
		prose.WriteString(line)
	}
	flush()
	return out.String()
}

func fenceMarker(s string) (byte, int) {
	if len(s) == 0 || (s[0] != '`' && s[0] != '~') {
		return 0, 0
	}
	n := 0
	for n < len(s) && s[n] == s[0] {
		n++
	}
	return s[0], n
}

func (c *conversion) inline(s string) string {
	var out strings.Builder
	start := 0
	for i := 0; i < len(s); {
		// Protect backtick spans unless the entire span is an invocation or path.
		if s[i] == '`' && !escaped(s, i) {
			n := 1
			for i+n < len(s) && s[i+n] == '`' {
				n++
			}
			end := strings.Index(s[i+n:], strings.Repeat("`", n))
			if end >= 0 {
				end += i + n
				out.WriteString(c.prose(s[start:i]))
				value := s[i+n : end]
				converted := value
				if c.standalone(value) && (i == 0 || s[i-1] != '!') {
					converted = c.prose(value)
				}
				out.WriteString(s[i : i+n])
				out.WriteString(converted)
				out.WriteString(s[end : end+n])
				i = end + n
				start = i
				continue
			}
			// An unmatched code delimiter is left untouched conservatively.
			out.WriteString(c.prose(s[start:i]))
			out.WriteString(s[i:])
			return out.String()
		}
		// Destinations can contain balanced parentheses and escaped delimiters.
		if i+1 < len(s) && s[i] == ']' && s[i+1] == '(' && !escaped(s, i) {
			end, depth := i+2, 1
			for end < len(s) && depth > 0 {
				if !escaped(s, end) {
					if s[end] == '(' {
						depth++
					}
					if s[end] == ')' {
						depth--
					}
				}
				end++
			}
			out.WriteString(c.prose(s[start:i]))
			out.WriteString(s[i:end])
			i = end
			start = i
			continue
		}
		if s[i] == '<' {
			if end := strings.IndexByte(s[i:], '>'); end >= 0 {
				end += i + 1
				out.WriteString(c.prose(s[start:i]))
				out.WriteString(s[i:end])
				i = end
				start = i
				continue
			}
		}
		i++
	}
	out.WriteString(c.prose(s[start:]))
	return out.String()
}

func (c *conversion) standalone(s string) bool {
	if loc := invocationRE.FindStringIndex(s); loc != nil && loc[0] == 0 && loc[1] == len(s) {
		return true
	}
	if loc := installedPathRE.FindStringIndex(s); loc != nil && loc[0] == 0 && !strings.ContainsAny(s, "\n\t ") {
		return true
	}
	return false
}

func escaped(s string, i int) bool {
	n := 0
	for i--; i >= 0 && s[i] == '\\'; i-- {
		n++
	}
	return n%2 != 0
}

func tokenStart(s string, i int) bool {
	if i == 0 {
		return true
	}
	r, _ := utf8.DecodeLastRuneInString(s[:i])
	return unicode.IsSpace(r) || strings.ContainsRune("([{'\"*,;!", r)
}

func tokenEnd(s string, i int) bool {
	if i == len(s) {
		return true
	}
	r, _ := utf8.DecodeRuneInString(s[i:])
	if unicode.IsLetter(r) || unicode.IsDigit(r) || strings.ContainsRune("_-/\\$@~%+=#?", r) {
		return false
	}
	if r == '.' && i+1 < len(s) {
		next, _ := utf8.DecodeRuneInString(s[i+1:])
		if unicode.IsLetter(next) || unicode.IsDigit(next) || next == '.' || next == '/' {
			return false
		}
	}
	return true
}

func (c *conversion) prose(s string) string {
	// URLs remain opaque even when embedded in ordinary prose.
	var out strings.Builder
	start := 0
	for _, loc := range urlRE.FindAllStringIndex(s, -1) {
		out.WriteString(c.tokens(s[start:loc[0]]))
		out.WriteString(s[loc[0]:loc[1]])
		start = loc[1]
	}
	out.WriteString(c.tokens(s[start:]))
	return out.String()
}

func (c *conversion) tokens(s string) string {
	// Collect replacements against the original text, avoiding a second pass over
	// generated paths (which may contain spaces or invocation-like segments).
	paths := installedPathRE.FindAllStringSubmatchIndex(s, -1)
	invocations := invocationRE.FindAllStringIndex(s, -1)
	type replacement struct {
		start, end int
		value      string
	}
	var replacements []replacement
	for _, loc := range paths {
		name := s[loc[2]:loc[3]]
		if !c.names[name] || !tokenStart(s, loc[0]) || !(tokenEnd(s, loc[1]) || loc[1] < len(s) && s[loc[1]] == '/') {
			continue
		}
		value := filepath.ToSlash(filepath.Join(c.dest, name))
		if value != s[loc[0]:loc[1]] {
			c.record("installed-skill paths")
		}
		replacements = append(replacements, replacement{loc[0], loc[1], value})
	}
	for _, loc := range invocations {
		name := s[loc[0]+1 : loc[1]]
		if !c.names[name] || !tokenStart(s, loc[0]) || !tokenEnd(s, loc[1]) || escaped(s, loc[0]) {
			continue
		}
		prefix := "$"
		if c.tool == "claude" {
			prefix = "/"
		}
		if prefix+name != s[loc[0]:loc[1]] {
			c.record("skill invocations")
		}
		replacements = append(replacements, replacement{loc[0], loc[1], prefix + name})
	}
	// Paths and invocations are separate, disjoint lists, but their order can mix.
	sort.SliceStable(replacements, func(i, j int) bool { return replacements[i].start < replacements[j].start })
	var out strings.Builder
	start := 0
	for _, r := range replacements {
		if r.start < start {
			continue
		}
		out.WriteString(s[start:r.start])
		out.WriteString(r.value)
		start = r.end
	}
	out.WriteString(s[start:])
	return out.String()
}
