# Agentic Browsing Auditor

Agentic Browsing Auditor helps an assistant audit and improve a page or frontend repository for Chrome Lighthouse Agentic Browsing readiness.

Use it when you need a web experience to work reliably for browser agents, not only for visual human browsing.

## Install the Skill

From the repository root:

```sh
./coreskills install --tool codex --skills agentic-browsing-auditor
```

Replace `codex` with `claude`, `copilot`, or `gemini` when you use a different tool.

## Run an Audit

Ask your assistant to use the skill against the current browser page, a local route, a live URL, or a frontend repository:

```text
Use $agentic-browsing-auditor to audit the current page or repository and improve its agentic browsing readiness.
```

For a local app, include the exact route:

```text
Use $agentic-browsing-auditor to audit http://localhost:5173/settings and improve its agentic browsing readiness.
```

## What the Auditor Checks

The skill focuses on the surfaces that make browser agents more deterministic:

| Surface | What the auditor looks for |
| --- | --- |
| WebMCP tools | Clear declarative or imperative tools for primary page tasks. |
| Form metadata | `toolname`, `tooldescription`, stable required field names, and useful `toolparamdescription` values. |
| Accessibility tree | Named buttons, links, inputs, selects, dialogs, and custom controls with semantic HTML first. |
| `llms.txt` | Concise root-level guidance that helps agents find key pages, task entry points, and docs. |
| Layout stability | Reserved space for media, embeds, async widgets, banners, and loading states that could move task controls. |

The detailed checklist lives in [`references/chrome-agentic-browsing-checklist.md`](references/chrome-agentic-browsing-checklist.md).

## How It Works

For a live or runnable page, the auditor opens the page in a browser, runs Lighthouse Agentic Browsing checks when available, inspects the main interaction flows, and records failing audit names or affected nodes before editing.

For a repository, the auditor traces routes, templates, components, forms, tool declarations, discoverability files, accessibility patterns, and layout-shift risks from source. It does not report a broad text match as a failure without checking the surrounding implementation.

## Finding Types

| Type | Meaning |
| --- | --- |
| Failure | Source or browser evidence shows a broken WebMCP schema, unnamed required field, unnamed interactive control, inaccessible task control, broken configured `llms.txt`, or server error for an expected discovery file. |
| Warning | The source suggests a risk that needs browser rendering, framework behavior, or runtime state to confirm. |
| Opportunity | The page works, but a WebMCP tool, better `llms.txt`, or more stable layout would make agent use more reliable. |

Missing `llms.txt` is an opportunity by default. It becomes a failure only when the site already advertises or implements the route and serves broken content or a server error.

## Report Format

A completed audit should separate:

- `Failures`: confirmed issues that can block agents or likely fail Lighthouse.
- `Warnings`: risks that need runtime confirmation.
- `Improvements made`: files changed and why.
- `Verification`: Lighthouse, browser, repository, and remaining verification gaps.

The auditor does not invent an Agentic Browsing score when Chrome or Lighthouse does not expose the experimental category.
