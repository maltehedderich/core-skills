# Frontend Design

Design and build web interfaces through a repeatable workflow: understand the task, reuse or establish a design system, finish a representative screen, then render, inspect, and refine it.

Use this for new screens, dashboards, landing pages, components, or an existing interface that needs better layout, typography, responsive behavior, or interaction polish. Small fixes stay small; established products keep their visual language.

## Install

From the repository root:

```sh
./coreskills install --tool codex --skills frontend-design
```

Replace `codex` with `claude`, `copilot`, or `gemini` for another tool.

## Use

Work from the product's repository so the assistant can inspect its tokens, components, content, and preview commands.

```text
Use $frontend-design to improve the settings screen. Keep its functionality and brand, and check the result at desktop and mobile widths.
```

```text
Use $frontend-design to build this app's first dashboard. Establish a small design system, document it in DESIGN.md, and inspect the implemented screen in the browser.
```

For a review without edits:

```text
Use $frontend-design to review this checkout flow and prioritize the changes that would improve its visual quality and usability. Do not modify files.
```

## What the workflow adds

- A visual direction tied to the product's task and content.
- A small implemented foundation when none exists, with a maintained `DESIGN.md` pointing to authoritative values and components.
- Refinement in order: composition, hierarchy, typography and spacing, surfaces, states, then optical detail and motion.
- Rendered review with concrete defects, fixes, and another look after the final edit.
- A handoff that identifies what was inspected and what remains unverified.

The skill prefers a suitable available browser or viewer. It includes an optional Playwright CLI route and uses the companion `playwright-cli` skill when available. It does not require a particular framework or install browser tooling automatically. Visual verification needs access to a rendered page or screenshot and a way to view it.

## Instructions and references

| File | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Workflow, scope, and completion criteria. |
| [design-contract.md](references/design-contract.md) | Establish or maintain a system without duplicating token sources. |
| [visual-craft.md](references/visual-craft.md) | Practical design decisions and symptom-based fixes. |
| [browser-review.md](references/browser-review.md) | Preview selection, Playwright CLI fallback, capture, and interaction checks. |
