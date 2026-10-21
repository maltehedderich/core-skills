# Rendered review and browser tooling

Use a real render to judge appearance, a DOM/accessibility snapshot to locate controls, and interactions to check behavior. Each provides different evidence.

## Choose the available route

1. Use a suitable connected browser, app preview, or viewer that can reach the target and provide visual inspection. Respect the user's selected browser and that tool's operating rules.
2. If none is suitable, use an installed Playwright CLI. If the `playwright-cli` skill is available, read it for environment-specific setup and commands. This skill remains usable without that companion skill.
3. If the CLI is absent but the project already has browser test or screenshot tooling, use that. Check current official setup instructions before adding tooling; do not install a new framework merely to capture one screen.
4. If rendering or image viewing is unavailable, complete source-level and available runtime checks, report the gap, and leave reproducible preview instructions. Capturing a PNG without viewing it does not count as visual inspection.

For native interfaces, substitute the relevant app preview or simulator. A browser mockup cannot verify native behavior.

## Prepare a useful render

Use the repository's existing development command and the actual reported local URL. Reuse a working server. Prefer local/test fixtures for submissions and failure states. Set representative content, theme, and state; wait for the relevant content, fonts, and assets to settle before capture. Do not rely on a fixed sleep when a readiness condition is available.

Keep artifacts in the project's existing review/output location or a temporary directory. Label captures with page, viewport, theme, and state when comparisons could be ambiguous. Before/after comparisons need equivalent content and dimensions. Do not commit temporary browser profiles, authentication state, logs, or screenshots by default.

## Playwright CLI fallback

The following is a starting sequence; replace the URL, output path, viewport, and session name for the task. Create the output directory first. Use the installed executable directly and verify flags with `playwright-cli --help` or `playwright-cli --help screenshot` when versions differ.

```sh
playwright-cli -s=frontend-review open http://localhost:3000
playwright-cli -s=frontend-review resize 1440 1000
playwright-cli -s=frontend-review snapshot
playwright-cli -s=frontend-review screenshot --filename=/tmp/frontend-review/desktop.png
playwright-cli -s=frontend-review resize 390 844
playwright-cli -s=frontend-review screenshot --filename=/tmp/frontend-review/mobile.png
```

**Open each saved image with the environment's image-viewing tool.** A terminal path and an accessibility snapshot cannot reveal visual balance, clipping, font appearance, or subtle alignment. Inspect the first viewport at normal size, then scroll and capture the rest as needed; a reduced full-page image can hide readability problems.

Use current snapshot references when interacting; refresh them after meaningful page changes. For example, after locating the actual primary action, focus it with keyboard navigation and activate it. Do not copy an example element reference into a different page.

```sh
playwright-cli -s=frontend-review press Tab
playwright-cli -s=frontend-review screenshot --filename=/tmp/frontend-review/focus.png
playwright-cli -s=frontend-review press Enter
playwright-cli -s=frontend-review snapshot
playwright-cli -s=frontend-review console
```

Check only themes the product supports, and inspect the reduced-motion behavior when movement is involved:

```sh
playwright-cli -s=frontend-review set-color-scheme dark
playwright-cli -s=frontend-review set-reduced-motion reduce
```

OS color-scheme emulation may not control an app with its own theme switch; operate that switch when needed. Clear emulation or restore the original state for subsequent comparisons. Resizing tests responsive layout; it does not reproduce touch input or every mobile-browser behavior.

Close only the session created for this review:

```sh
playwright-cli -s=frontend-review close
```

Command references: [official CLI skill](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/SKILL.md) and [CLI reference](https://github.com/microsoft/playwright-cli/blob/main/README.md). Prefer the installed version's help when command availability differs.

## Review cases

Select cases according to the change, rather than running an exhaustive matrix for a small edit:

| Case | What to inspect |
| --- | --- |
| Normal desktop and narrow layout | Scan order, widths, grouping, wrapping, navigation, action visibility, accidental horizontal overflow. |
| At layout transitions | Just above/below a stacking or navigation change; no overlap or lost information. |
| Realistic content extremes | Long names/labels, missing images, large values, empty results, and enough rows to scroll. |
| Primary task | Pointer and keyboard use, visible focus, loading, completion, validation, and relevant failure recovery. |
| Overlays, when affected | Focus entry/return, dismissal, scrolling, stacking, and fit in small viewports. |
| Motion, when affected | Reduced motion, repeated/rapid input, interrupted transitions, and stable layout. |
| Supported themes and enlarged text | Contrast, state visibility, readability, and reflow without lost actions. |

For motion, watch the interaction or a short recording; a still only proves a frame. For behavior, exercise the flow; screenshots cannot establish that a button works. Use existing automated checks where useful, but do not mistake successful tests for visual review.

Record the most consequential visible defects, fix them, and recapture the same cases. Finish by identifying the actual viewports, states, interactions, and checks inspected, plus anything unavailable. Avoid claims such as “fully responsive” or “accessible” without the evidence those claims require.
