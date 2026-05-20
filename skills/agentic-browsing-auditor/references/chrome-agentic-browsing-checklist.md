# Chrome Agentic Browsing Checklist

Source basis: Chrome Developer documentation for Lighthouse Agentic Browsing scoring, WebMCP registration, declarative form metadata, schema validity, `llms.txt`, accessibility for agents, layout stability, and WebMCP best practices. Re-check the current official docs when exact audit names or API details matter.

## Scoring Model

Chrome's Agentic Browsing category is experimental. Lighthouse does not currently compute a weighted 0-100 score for it. It reports a fractional pass ratio, pass/fail audit status, warnings, and informational counts. Treat the score as a progress signal, not as a final quality grade.

Results can fluctuate when WebMCP tools register dynamically, when DOM/accessibility tree complexity changes, or when cumulative layout shift moves target elements between identification and interaction.

If the category or audit is unavailable in the current tooling, report that limitation directly. Do not translate other Lighthouse categories into an agentic browsing score.

## Audit Surfaces

### WebMCP integration

Lighthouse observes WebMCP registration through Chrome DevTools Protocol and recognizes declarative and imperative tools.

Ensure:

- Important task flows have explicit tools.
- Tool names are clear, action-oriented, and non-overlapping.
- Tool descriptions explain what the tool does and when to use it.
- Imperative tools include `name`, `description`, `inputSchema`, and reliable execution behavior.
- Dynamically registered tools appear before Lighthouse snapshots or are verified manually.

### Declarative form metadata

Lighthouse identifies forms missing declarative WebMCP metadata. A tool form needs both `toolname` and `tooldescription`; omitting one unregisters the tool or fails schema validity.

Ensure:

- Every primary task form has both attributes.
- Every required control in a tool form has a stable `name`.
- Controls have labels, and fields whose purpose is not obvious include `toolparamdescription`.
- Select options and enum-like controls use human-meaningful values/titles.

### WebMCP schema validity

Lighthouse fails schema validity when:

- A form has `tooldescription` without `toolname`.
- A form has `toolname` without `tooldescription`.
- A required form field lacks `name`.

It can warn when optional named fields lack both `toolparamdescription` and an associated label.

### `llms.txt`

The root `llms.txt` is optional in Lighthouse today: a 404 is marked not applicable, but server errors are flagged. Adding it improves discoverability and reduces crawling needed for agents to understand the site.

Ensure:

- The production root serves `llms.txt`.
- The file is concise Markdown.
- It includes site purpose, key pages, docs/API references, important task entry points, and relevant constraints.
- It does not expose private/internal-only information.

Classify missing `llms.txt` as an opportunity by default. Classify a server error, broken configured route, or malformed published file as a warning or failure depending on impact.

### Accessibility for agents

Agents use the accessibility tree to identify interactive elements. Prioritize:

- Programmatic names for all buttons, links, inputs, selects, textareas, menus, dialogs, and custom controls.
- Semantic HTML before ARIA.
- Valid roles and parent/child role relationships.
- No interactive element hidden from the accessibility tree.
- Labels that describe the actual action or expected input.

### Layout stability

Agents may use screenshots and coordinate-based interaction. Layout shifts can cause an agent to click or type in the wrong place.

Ensure:

- Images, video, iframes, embeds, ads, and async widgets reserve dimensions or aspect ratio.
- Late content is not injected above active controls without reserving space.
- Fonts, skeletons, loading states, and hydration do not resize task-critical controls.
- CLS is measured in live Lighthouse/Web Vitals checks when possible.

## Caveats

The WebMCP API and Lighthouse Agentic Browsing category are experimental. Prefer progressive enhancement: site functions must still work without WebMCP support. Do not weaken human accessibility or security to satisfy agent access.
