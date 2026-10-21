# Establish and maintain the design contract

Read this when a project lacks a usable design foundation, shared rules need to change, or sources disagree. The contract should let the next contributor build a related screen without guessing its appearance or behavior.

## Discover before defining

Look for design guidance at the relevant app or package scope, theme variables, token packages, component variants, component galleries, and representative shipped screens. A missing `DESIGN.md` does not imply a missing system.

| Starting point | Action |
| --- | --- |
| Established system and guidance | Follow them. Update the relevant rule only when the task changes it. |
| Consistent implementation, little documentation | Record the existing roles and their source paths. Add only the guidance needed for the work. |
| Conflicting documents or inconsistent UI | Follow any declared authority policy. Otherwise preserve established behavior for a local fix, identify the conflict, and scope proposed changes explicitly. |
| New product or no coherent foundation | Choose a small token set and reusable primitives, implement them, and record their intended use. |

Label observed facts, inferred intent, and proposals separately. Estimated values from a screenshot are not authoritative tokens. Do not assign a fictitious owner or claim a proposed direction has been approved.

## Build the minimum useful system

Set enough constraints to make the representative screen coherent:

- Semantic colors for canvas, surface, text, muted text, border, accent, focus, and relevant status roles; include approved foreground/background pairs.
- Typography roles with family/fallback, size, weight, line height, and purpose. Choose explicit treatments for numbers or long-form reading when relevant.
- Spacing steps, content widths, gutters, alignment, and density; define how groups relate.
- A small set of radii and surface treatments. Explain what elevation means.
- The controls needed by the core task, including focus, pressed, disabled, loading, and error behavior where applicable.

Put these into the project's actual styling mechanism before repeating them across screens. A CSS theme and a few shared controls can be sufficient; do not add a component framework or token generator just to satisfy this workflow. Extend after the first rendered screen proves the foundation.

## Choose one source for exact values

Prefer an existing token package or theme as the editable source. `DESIGN.md` explains roles, combinations, exceptions, and implementation links. Reference token names rather than manually duplicating every value.

A specification-led system is also possible if the project already exports its tokens into code. Identify the exporter, generated files, and validation command. Never leave two independently editable palettes and hope they stay aligned.

Plain Markdown is sufficient unless the project needs format interoperability. If it uses the [Google DESIGN.md format](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md), follow its selected schema version and validation tooling. That format supports structured tokens alongside rationale; a filename alone does not imply schema compliance. Verify its current documentation before adding format-specific commands or changing a pipeline.

## Write rules that resolve decisions

Use **rule → reason → implementation/example → exception** when the rationale is not obvious. Distinguish required behavior from defaults and optional treatments.

For example: “Use the shared numeric-cell treatment for monetary columns so amounts align by place value. It uses tabular numerals and end alignment. Narrative table cells retain the body-text style.” Link the actual component or token source when it exists.

Record transformations instead of saying “responsive”: which columns stack, their reading order, where actions move, how navigation collapses, and how tables overflow. Record behavior instead of just screenshots: during submission, prevent duplicate requests, keep the action's width stable, and preserve inputs after failure.

## Adaptable document outline

Include sections that settle recurring decisions. Combine or omit irrelevant sections; do not ship an empty template.

```markdown
# Design

## Scope and authority
Product/app governed; status; maintainer if known.
Canonical token and component paths; conflict-resolution policy.

## Product character
Users, core task, density, and visual direction.
A few principles with visible consequences and reasons.

## Foundations
Semantic color roles and approved pairings; theme behavior.
Typography roles, font sources/fallbacks, numbers, and wrapping.
Spacing, widths, gutters, grouping, shape, and meaningful elevation.
Link exact values to their editable source.

## Layout and components
Page patterns, reusable components, and variant selection.
Responsive transformations, overflow, and content extremes.
Relevant interaction, loading, empty, success, and failure states.

## Accessibility and motion
Target, approved contrast pairs, focus, keyboard, and labeling.
Motion purpose, timing/easing roles, and reduced-motion behavior.

## Assets and content
Icon/imagery sources and treatment; product-specific writing rules.

## References and verification
Approved screens/stories and what each establishes.
Preview command, relevant checks, and representative review cases.
For screenshots: viewport, theme, state, and current/proposed status.

## Maintenance
Where edits begin, what is generated, and how to check agreement.
Scoped exceptions and the condition for removing them.
```

Prefer links to real paths over speculative component inventories. If ownership is unknown, say so or omit it; record the implemented decision without inventing organizational approval. Separate accepted rules from proposals and migration notes.

## Keep it discoverable and synchronized

Use the repository's existing guidance entry point. When establishing a new contract as part of the requested work, add a short scoped pointer in the appropriate instruction file if needed, such as: “For dashboard UI changes, read `apps/dashboard/DESIGN.md` and reuse its linked tokens and components.” Preserve unrelated instructions. Do not create overlapping instruction files merely to repeat this paragraph.

Update guidance in the same change as shared visual rules. Verify links, token/source agreement, and whether a representative screen can be implemented from the rules. Fix the ambiguities that forced guesses. A schema linter, when used, complements rendered and behavioral review.
