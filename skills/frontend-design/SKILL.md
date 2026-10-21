---
name: frontend-design
description: "Design, implement, and refine polished web interfaces: new screens, components, dashboards, landing pages, and visual redesigns. Use when UI quality, layout, typography, responsive behavior, or interaction polish is part of the task, including requests to make an interface look better. Reuses or establishes a design system and verifies the rendered result. Not for backend-only work or logic changes with no visual impact."
---

# Frontend Design

Build interfaces whose composition, typography, states, and interactions feel deliberately chosen for the product. Work from the user's task through a small design system into a rendered, inspected implementation. Treat the first render as a draft.

## Choose the right amount of process

| Request | Approach |
| --- | --- |
| New interface or substantial redesign | Establish the direction and foundation, finish one representative screen, then extend it. |
| Improve an existing interface | Inspect it first, identify the largest visible weaknesses, and refine within its established system. |
| Small component or styling fix | Read the relevant tokens and component, make the focused change, inspect the affected states and sizes. |
| Review only | Inspect available evidence and return prioritized findings with concrete fixes. Do not modify files. |

Keep the requested product, stack, functionality, and scope. A small UI task does not require a new design system, document, dependency, or approval meeting. Continue through implementation and verification when those are requested.

## 1. Understand the task and inspect the starting point

Read project instructions, applicable design guidance, theme/token files, shared components, and nearby screens. Inspect the live UI or supplied visual references when available; for existing UI, capture the affected view before changing it. Determine the actual development and preview commands from the repository.

Establish a short working brief:

- Who uses this screen, what they need to accomplish, and which action or information should lead.
- The real content, relevant states, viewport constraints, and any supplied visual direction.
- What already works and what the change should improve.

Infer routine choices from the product and existing work. Ask only for missing information that would materially change the result. If evidence conflicts, distinguish observed implementation, documented intent, and proposed changes; do not silently canonize an old screenshot or inconsistent component.

Choose a preview route early. Prefer a suitable available browser, app preview, or connected viewer. If it cannot render and inspect the target, use the Playwright CLI fallback in [browser-review.md](references/browser-review.md). For native app work, use the platform's preview or simulator tooling instead of assuming a browser is sufficient.

## 2. Set a visual direction and establish the foundation

For new work, translate the intended character into visible decisions. “Calm and precise” might mean a compact navigation rail, tabular figures, restrained status color, and generous separation between work areas. An editorial product may instead rely on reading width, expressive headings, and image crops. Choose composition and density for the task; familiar card grids, gradients, oversized headings, and glass effects need a product-specific reason.

Use supplied references to extract specific relationships: type contrast, alignment, density, image treatment, or surface layering. Preserve their intent without copying unrelated branding or content. When no direction is established, briefly compare distinct compositions and choose one; do not make the user approve routine aesthetic decisions.

If a usable system exists, reuse its canonical tokens and components. Extend it only where the task reveals a gap. If none exists, define and implement a small foundation before spreading styles across screens: semantic color roles, typography roles, spacing, layout widths, shape/elevation, and control states. Start with the primitives needed by the core task.

Read [design-contract.md](references/design-contract.md) when creating a foundation, resolving conflicting guidance, or changing shared design decisions. Use it to create or update a scoped `DESIGN.md` that records decisions, reasons, implementation locations, and verification. Keep exact values in one editable source. Existing equivalent guidance can serve this role.

## 3. Build one representative slice

For new screens or substantial polish, read [visual-craft.md](references/visual-craft.md). For a small fix, consult only the relevant section if needed.

Start with the core task and realistic content, including a plausible long or awkward case. Build enough structure to judge the composition in the real medium. For new compositions, check hierarchy in grayscale or subdued color before adding accents; preserve semantic cues in the shipped UI.

Refine in this order:

1. Composition, reading order, grouping, and density. The main task should be apparent without explanation.
2. Typography, alignment, and spacing. Make secondary content quieter while keeping it readable.
3. Color, assets, surfaces, and depth. Each treatment should reinforce the hierarchy or product character.
4. Component states and responsive transformations. Preserve useful information and actions as space changes.
5. Optical details and purposeful motion. Add movement only where it clarifies feedback, relationships, or continuity.

Use the project's shared components and native semantics. Choose heading levels for document structure and style them for visual hierarchy. Keep real behavior intact; attractive dead controls are unfinished work. Use local fixtures for prototypes and identify simulated behavior.

Finish and inspect one representative slice before propagating its patterns. This exposes weak choices before they become repeated components. Small changes can go directly to the affected component.

## 4. Render, inspect, and revise

Use [browser-review.md](references/browser-review.md) for capture mechanics and interaction checks. A build, DOM snapshot, or screenshot file alone does not establish visual quality: open and examine the rendered image or live view.

Review at the intended desktop and narrow widths, plus any size where the layout changes. Use relevant themes and states; keep the review proportional to the change. Examine the first viewport at normal viewing size, then the rest of the page and affected details. Exercise the primary task with pointer and keyboard.

Write a short internal defect list tied to observable evidence. “At 390 px the fixed toolbar hides the submit action” is useful; “needs more polish” is not. Review in this order:

| Priority | Look for |
| --- | --- |
| Task and usability failures | Missing or broken actions, unreadable content, keyboard traps, clipped controls, inaccessible focus or feedback. |
| Composition and hierarchy | Competing focal points, weak grouping, inappropriate density, unclear scan order, poor narrow-screen composition. |
| System and craft | Inconsistent roles or spacing, mismatched components, muddy surfaces, poor asset crops, optical alignment, awkward motion. |

Fix the highest-impact issues, render again, and compare equivalent states. Continue until the observed issues within scope are resolved; avoid indefinite aesthetic churn. Do not hide a usability failure behind an average score. If runtime or viewing tools are unavailable, complete the work that can be checked and explicitly report which visual or behavioral checks remain unverified.

## 5. Deliver the implementation and evidence

Run the project's checks relevant to the change. Recheck the rendered UI after the final visual edit. Update the design contract when shared decisions changed, including where to edit them and how to verify them.

Report what changed and why, the screens/states/sizes actually inspected, and any remaining limitation. Link useful screenshots or preview artifacts when the environment supports them. Keep proposed improvements separate from completed work. Never claim visual verification solely from source inspection or successful compilation.
