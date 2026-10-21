# Visual craft in implementation

Use these decision rules while building or diagnosing a screen. Existing product conventions and explicit user direction take precedence over the starting values here.

## Composition and hierarchy

Design the feature's useful content first. Give the main task or information a clear place in the reading order, then arrange supporting controls around it. Repeated card containers can obscure relationships; use alignment and spacing for grouping, and a separate surface when it communicates an independent region or state.

Combine position, weight, size, and contrast. Before enlarging the headline or primary button, reduce competing emphasis in metadata, borders, icons, and secondary actions. Keep secondary text readable. If every region asks for attention, decide what a user should see first and quiet the rest.

Check the composition with color suppressed. It should retain a clear path through the content. Restore semantic colors and non-color indicators before delivery. Preserve meaningful HTML structure while controlling visual weight through styles.

## Spacing and density

Use a limited spacing scale with finer increments for small elements and larger jumps for sections. A starting set such as `4, 8, 12, 16, 24, 32, 48, 64` CSS pixels is useful when no system exists; it is not a ban on borders, optical corrections, or fluid dimensions. Repeated exceptions usually indicate a missing token or a weak layout rule.

Space between groups should exceed space within a group. When a screen feels cramped, try a more generous version, then tighten related elements together. Judge it at the intended viewport. Dense operational tools need compact rows and visible data; marketing and reading surfaces can allow more space. Do not double every gap mechanically.

Align text edges and controls to a small set of anchors. Use padding and layout rules instead of accumulated per-element offsets. Keep a coherent vertical rhythm, including the relationship between headings, descriptions, fields, and actions.

## Typography

Choose a small set of roles instead of styling each label independently. An initial body size around `16px`, a compact metadata role, and clearly separated heading roles can work; adjust for the font, content, audience, and density. Use relative units where text should scale with user preferences.

One well-chosen family and a restrained set of weights are often enough. Additional display or monospace faces need a defined role. Check the loaded font and fallback in the actual page: font metrics change wrapping, alignment, and perceived weight.

Tune line height to text length and size. Body copy needs room for repeated lines; large headings can be tighter. Avoid applying display tracking to small text. Limit reading width, allow labels to wrap sensibly, and use tabular figures for columns of changing or comparable numbers. Avoid truncating information the user needs to make the decision.

## Color, materials, and depth

Choose semantic roles and a limited set of shades. HSL or perceptual color spaces can help create related shades, but equal numeric steps do not guarantee equal perceived contrast. Check actual foreground/background pairs in each theme.

Reserve strong accents for intentional emphasis and use separate status roles. On tinted surfaces, harmonize secondary text, borders, and shadows with the surface hue while retaining sufficient contrast. Random neutral grays can look muddy; excessive tint can impair readability.

Where elevation communicates structure, use coherent lighting: raised surfaces may have a subtle upper highlight and shadows below; inset controls can reverse the cue. Combine a fine edge with restrained near/far shadows if needed. Flat surfaces are appropriate when spacing, contrast, or separators already establish the layers. Dark themes often need surface separation more than stronger black shadows.

Choose a few corner treatments. For nested rounded surfaces, an inner radius near the outer radius minus the inset is a useful starting point; inspect the resulting curve and clamp it sensibly. Use optical judgment for icons, asymmetric glyphs, and small offsets instead of forcing every shape onto mathematical centers.

## Assets and product character

Use the product's own content, brand assets, and a consistent icon family. Align icon stroke, size, and optical weight with nearby type. Inspect image resolution, focal point, aspect ratio, and crop at each important layout. Avoid stretched logos and placeholder imagery that survives into delivery unintentionally.

Express character through a coherent set of choices: composition, type, density, imagery, and repeated interaction behavior. Decorative gradients, texture, illustrations, or unusual shapes should support that direction. No font or palette is universally required or forbidden.

## States and motion

Make interactive affordances and state changes visible. Hover is an enhancement; touch and keyboard users also need feedback. Provide focus that survives clipping, readable selected/disabled states, and clear errors with a path to recovery. Loading should preserve useful geometry; feedback should not make controls jump.

Use motion to explain a change, connect spatial relationships, or acknowledge input. Repeated keyboard actions and high-frequency operations often benefit from immediate response. A starting range of `100–300ms` suits many small transitions, with shorter feedback for direct input; distance and purpose determine timing.

Prefer a decisive ease-out for entering or responding and a suitable ease-in-out for continuous repositioning. Inspect the actual curve; a custom cubic Bézier is a tool, not a quality guarantee. Small press scales and subtle proportional entry scales preserve object identity. Set transform origins to the trigger or attachment edge for popovers. Avoid scaling readable content from zero.

Use small staggered delays only when sequence helps comprehension, without delaying access to controls. Prefer transform/opacity where suitable, avoid broad `transition: all`, and check interruption, rapid repeat actions, closing mid-transition, and layout shifts. Reduced-motion behavior should preserve state feedback while removing unnecessary spatial movement.

## Accessibility checks that constrain the visual system

Follow the project's accessibility target. If none is stated, use WCAG 2.2 AA as a working web baseline and report only the checks actually performed. Normal text generally needs `4.5:1` contrast; qualifying large text needs `3:1`. Relevant control boundaries and state indicators need `3:1` under the non-text criterion. The AA minimum pointer-target criterion uses `24 × 24` CSS pixels with exceptions, including spacing; larger touch targets can be a product default. Reflow, visible focus, keyboard operation, and non-color feedback also constrain the layout. Check the applicable criteria in [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

Keep labels and accessible names meaningful. Do not use low opacity as the only hierarchy technique, remove focus for aesthetic reasons, or replace semantic controls with clickable containers. Perceptual contrast tools can supplement the required contrast checks; they do not substitute for the chosen conformance method. A screenshot or automated scan alone cannot establish accessibility compliance.

## Diagnose before decorating

| Visible symptom | First adjustment to try |
| --- | --- |
| Everything looks equally important | Reduce metadata, borders, and secondary-action emphasis; strengthen grouping and position. |
| Screen feels busy despite few elements | Increase separation between groups; remove redundant containers or separators. |
| Screen feels empty or inefficient | Reconsider width, density, and content placement before adding decoration. |
| Design looks inconsistent | Compare shared roles: spacing, type, controls, radii, and icon treatment. Fix the source. |
| Narrow layout feels like a shrunken desktop | Recompose navigation, columns, action placement, and overflow in reading order. |
| UI looks polished but feels fragile | Exercise focus, errors, loading, rapid input, and interrupted motion. |

Change the underlying rule when the symptom repeats. For a local optical issue, a local correction can be appropriate.
