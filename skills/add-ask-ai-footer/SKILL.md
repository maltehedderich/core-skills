---
name: add-ask-ai-footer
description: Add an "Ask AI about [brand/site]" footer or near-footer section to websites and web apps. Use when Codex needs to implement AI summary links for Google AI or Gemini, Claude, ChatGPT, Grok, and Perplexity; adapt the prompt to the target website's canonical URL and entity type; source brand icons from @iconify-json/simple-icons; and match the existing page or footer styling.
---

# Add Ask AI Footer

## Overview

Add a compact footer block that opens AI assistants with a prefilled prompt asking for a concise summary of the current company, product, person, project, or website. Treat the ELECTE pattern as a reference for behavior, not as a visual template to copy.

Read [providers.md](references/providers.md) before implementing provider URLs and icon names.

## Workflow

1. Inspect the target project and footer:
   - Find the canonical footer, site layout, or shared shell component.
   - Reuse the app's framework, routing, styling system, button component, icon wrapper, and package manager.
   - Place the section where users naturally expect secondary footer actions, usually after footer navigation and before legal/status/resource links.

2. Derive the prompt inputs:
   - Use a production canonical URL when the user provides one.
   - If no URL is provided, derive it from site metadata, deployment config, canonical link tags, sitemap config, or environment defaults.
   - Ask the user for the URL only when the project cannot reveal a real public URL. Do not hard-code localhost, preview URLs, or staging URLs into the final prompt.
   - Derive the display label from existing brand, logo, metadata, or footer text. Use uppercase only when the brand does.
   - Choose the noun in the prompt to fit the site: `company`, `product`, `person`, `project`, or `website`.

3. Use this prompt shape unless the user requests another:

   ```text
   Please provide a concise summary of this {entity_type}: {canonical_url}. Include the main points, key insights, and conclusions.
   ```

4. Implement real links:
   - Prefer static anchor `href` values generated from `encodeURIComponent(prompt)` so links work with middle-click, keyboard navigation, copy link, and disabled JavaScript.
   - Use `target="_blank"` with `rel="noopener noreferrer"` when opening external AI tools in a new tab.
   - Add descriptive `aria-label` values such as `Ask ChatGPT about {brand}`.
   - Avoid click-only handlers unless the app already centralizes outbound link tracking or the canonical URL must be computed client-side.

5. Use Simple Icons through the existing icon pipeline:
   - Add `@iconify-json/simple-icons` if the project uses Iconify, unplugin-icons, Tailwind Iconify, or another Iconify-compatible build-time icon flow.
   - Use existing imports or component conventions, for example `simple-icons:claude`, `~icons/simple-icons/claude`, or `i-simple-icons-claude` depending on the stack.
   - Do not paste provider SVG path data unless there is no viable Iconify-compatible renderer and the user accepts a local fallback.
   - If a requested provider has no Simple Icons entry, prefer the documented fallback from `providers.md` or ask before adding a non-Simple-Icons asset.

6. Match the site design:
   - Adapt typography, spacing, border radius, colors, hover states, focus states, density, and responsive behavior to the existing footer.
   - Keep the block visually subordinate to the main footer CTA and navigation.
   - Use a heading like `Ask AI about {BRAND}` and compact icon-plus-label buttons when space allows.
   - On narrow screens, wrap buttons cleanly. Use icon-only buttons only when labels no longer fit and provide accessible names/tooltips.
   - Preserve contrast and focus visibility.

7. Verify the change:
   - Run the relevant formatter, typecheck, tests, and build for the project.
   - Manually inspect desktop and mobile footer layouts.
   - Confirm every generated link contains the encoded production URL and opens the intended AI tool.
   - Confirm no footer text overlaps, wraps awkwardly, or shifts layout on hover.
