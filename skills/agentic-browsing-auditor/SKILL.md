---
name: agentic-browsing-auditor
description: Verify and improve a website, current page, or frontend repository for Lighthouse Agentic Browsing readiness. Use when asked to audit, raise, improve, or debug agentic browsing level, WebMCP readiness, llms.txt discoverability, agent-accessible forms, accessibility-tree quality for agents, or layout stability for AI/browser agents.
---

# Agentic Browsing Auditor

## Core Idea

Optimize the page for deterministic machine interaction, not only visual browsing. Treat Chrome's experimental Lighthouse Agentic Browsing category as a readiness checklist: expose structured tools, keep forms self-describing, make the accessibility tree complete, reduce layout shifts, and publish a root `llms.txt`.

Read `references/chrome-agentic-browsing-checklist.md` when you need the detailed scoring notes or implementation heuristics.

## Workflow

1. Identify the target: a live page, current browser page, local dev server route, static HTML file, or repository.
2. If the page is live or runnable, inspect it in a browser first:
   - Open the page in Chrome or the in-app browser.
   - Run Lighthouse Agentic Browsing audits when available.
   - If the Agentic Browsing category is unavailable, do not invent a substitute score; use browser inspection and repository evidence instead.
   - Capture the failing audit names and exact nodes/forms/tools before editing.
   - Inspect visible interaction flows and accessibility names for the primary tasks.
3. If working from a repository, inspect the implementation directly:
   - Search for page routes, templates, components, forms, custom buttons/links, modal/dialog components, and file-serving routes.
   - Search for WebMCP declarations: `toolname`, `tooldescription`, `toolparamdescription`, and `navigator.modelContext.registerTool`.
   - Search for discoverability files or routes: `llms.txt`, `robots.txt`, sitemap generation, docs indexes, API references, and public route manifests.
   - Search for layout-shift risks: images/media/iframes without stable dimensions, late-loaded widgets, hydration-only content, ad slots, banners, toast regions, and skeletons.
   - Search for accessibility risks: icon-only buttons, clickable non-buttons, custom selects/comboboxes, `aria-hidden`, `role`, `tabindex`, and controls without labels.
4. Fix the highest-leverage issues in this order:
   - Broken WebMCP schemas: partial `toolname`/`tooldescription`, required controls without `name`, malformed imperative registrations.
   - Missing WebMCP coverage on primary task forms.
   - Missing programmatic names for buttons, links, inputs, and other interactive controls.
   - Layout instability risks, especially media without dimensions and injected content above task controls.
   - Missing or weak `llms.txt` as a discoverability improvement unless a configured route/server error makes it a confirmed failure.
5. Re-run live checks when available. If no live page is available, report repository findings as static evidence and mark browser/Lighthouse verification as not run.

## Repository Inspection

Use source inspection to find the code paths that define the page, then judge each issue from the surrounding framework patterns. Do not rely on broad regex matches alone; trace components through props, wrappers, and generated routes before calling something a failure.

Useful search targets:

- `toolname`, `tooldescription`, `toolparamdescription`, `registerTool`, `modelContext`
- `<form`, `required`, `name=`, `type="submit"`, form actions, server actions, validation schemas
- `<button`, `role="button"`, `onclick`, `on:click`, `@click`, `tabindex`, icon button components
- `<input`, `<select`, `<textarea`, `aria-label`, `aria-labelledby`, `<label`
- `<img`, image components, `iframe`, `video`, `aspect-ratio`, `width`, `height`, lazy-loaded media
- `llms.txt`, `robots.txt`, `sitemap`, public/static asset directories, route handlers

Classify findings:

- `Failure`: the source clearly creates an invalid WebMCP schema, unnamed required field, unnamed interactive control, inaccessible task control, broken configured `llms.txt` route, or server error for an expected public discovery file.
- `Warning`: the source suggests a risk but needs browser rendering, framework resolution, or runtime state to confirm.
- `Opportunity`: the page works, but a clear WebMCP tool, new or better `llms.txt`, or more stable layout would make agent use easier.

## Improvement Rules

### WebMCP tools

Prefer declarative WebMCP for normal HTML forms. Add both attributes together:

```html
<form toolname="newsletter_signup" tooldescription="Subscribes the user to the newsletter">
  <label for="email">Email</label>
  <input id="email" name="email" type="email" toolparamdescription="The user's email address" required>
  <button type="submit">Sign up</button>
</form>
```

Use imperative `navigator.modelContext.registerTool` only for dynamic tools, non-form actions, stateful flows, or actions that need custom execution. Keep each tool single-purpose, action-oriented, and available only in page states where it can actually run.

### Forms and schemas

Every tool form must have both `toolname` and `tooldescription`. Every required form field inside a tool form must have a stable, unique `name`. Prefer explicit `toolparamdescription` for fields whose purpose is not obvious from an associated label.

### Accessibility tree

Agents rely on the accessibility tree as their page model. Make every interactive element discoverable by role and name: use semantic HTML, visible labels, `aria-label`/`aria-labelledby` only when needed, valid ARIA relationships, and no focusable or clickable controls hidden from assistive technology.

### `llms.txt`

Add `llms.txt` at the served domain root when it would improve agent discoverability. Treat absence as an opportunity by default, not a failure. Treat it as a failure only when the site already advertises or implements the route and it returns a server error or broken content. Keep it concise Markdown with the site's purpose, canonical key pages, task entry points, docs/API references, and any constraints agents need to know. Avoid dumping entire docs or private/internal-only locations.

### Layout stability

Reserve space for images, video, embeds, ads, async widgets, and late content. Set dimensions or aspect ratios, avoid inserting content above active controls after load, and make skeleton/loading states size-stable.

## Reporting

Lead with confirmed failures and the user-visible impact for agents. Include file/line references for repository findings. Separate:

- `Failures`: likely to fail Lighthouse or block agents.
- `Warnings`: may reduce reliability or need manual confirmation.
- `Improvements made`: exact files changed.
- `Verification`: live Lighthouse/browser checks, repository inspection, and any remaining gaps.
