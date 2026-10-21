# Motion design craft for product films

The eight practices behind an expensive-feeling SaaS or app film, with starting values. The timing values and shot recipes are starting points to adjust for the brand, the content and the placement, not rules. A project's own studio rules take precedence.

## Contents

- Core idea and sources
- 1. Exceptional key frames
- 2. A visible transformation and a signature behavior
- 3. The interface as product photography
- 4. Timing and spacing
- 5. Attention and reading time
- 6. Transitions that carry the idea
- 7. Depth, lighting and finish
- 8. Sound with the picture
- Field-tested defaults

## Core idea and sources

An expensive-feeling film gives the impression that every frame, movement and sound was chosen deliberately for this product. The strongest combination is exceptional still design, controlled attention, a recognizable motion personality, and enough breathing room to appreciate the result.

This guidance synthesizes these practitioners:

- **Jorge R. Canedo Estrada / Ordinary Folk:** product-film craft where message, visual development, animation and audio are connected from the beginning ([process](https://www.ordinaryfolk.co/process); [Webflow Ecommerce](https://www.ordinaryfolk.co/project/webflow-ecommerce)).
- **Ben Marriott:** composition, hierarchy, easing, the graph editor, and the progression from storyboard to finished animation ([Design Breakthrough](https://www.benmarriott.com/design-breakthrough)).
- **Sander van Dijk:** transitions and continuity, treating shots as parts of one continuous film with a shared direction and rhythm ([School of Motion podcast](https://schoolofmotion.com/blog/sander-van-dijk-podcast)).
- **BUCK:** distinctive brand systems whose shapes and motion behaviors come from how the product works ([Comfy brand refresh](https://buck.co/work/comfy-brand-refresh)).
- **Val Head:** motion choices tied to purpose and personality: directing attention, preserving continuity, expressing calm, confidence or playfulness ([Purpose and style](https://noti.st/valhead/OrOO13/purpose-and-style-using-motion-with-meaning-in-interfaces)).
- **Wesley Slover and Trevor Richardson / Sono Sanctus:** sound that gives motion weight and character, making room in the music and choosing which moments get sonic emphasis ([School of Motion podcast](https://schoolofmotion.com/blog/sono-sanctus-podcast-podcast)).

## 1. Exceptional key frames

**Why:** Composition, hierarchy, color and typography set the visual quality of the whole film. Motion cannot rescue a weak frame; it only shows it for longer.

**How:** Before detailed animation, fully design the opening, the strongest product moment and the closing frame. For each:

- **One visual hero.** Give the product, headline or result the strongest combination of size, contrast and position.
- **A deliberate type hierarchy.** Start with one type family, two weights, and distinct headline, supporting-copy and UI sizes. Refine line breaks, spacing and optical alignment.
- **Room for the hero.** Use empty space to separate it from supporting information. Make background detail quieter where the viewer needs to read.
- **Consistent rules.** Carry the same palette, corner treatment, icon weight, spacing logic and lighting character across the sequence.

**Test:** View the three frames together at the intended viewing size. They should already look like a coherent campaign.

## 2. A visible transformation and a signature behavior

**Why:** A distinctive idea gives the craft something to express. BUCK's Comfy system derives its motion language from the product's modularity and from the way individual inputs become creative outcomes.

**How:** Write the promise as:

> **[Product] turns [recognizable input or difficulty] into [a valuable, visible result].**

Then choose two or three motion verbs that express the transformation:

- An automation product might **trigger, propagate, resolve**.
- A collaboration product might **gather, align, advance**.
- An analytics product might **collect, organize, reveal**.

Reuse that behavior in the product demonstration, the transitions and the final brand moment. Keep the same information identifiable throughout the sequence; that continuity makes the demonstration convincing.

How the before and after behave matters as much as how they look. A locked or empty state can be flat, grey and still, while the earned state has color, weight and lands on the beat.

## 3. The interface as product photography

**Why:** The interface is often the object being sold. Strong product films combine dimensional richness with a clear focus on the message and the actual product UI.

**How:**

- **Build intentional shots from the real interface.** Isolate the relevant components. Remove browser chrome, incidental notifications and unrelated content.
- **Use specific, plausible content.** A meaningful task title or a recognizable document explains the benefit better than placeholder text.
- **Vary the framing.** A close view for an important action, a medium view for its response, a wider view for the resulting workflow.
- **Keep the information plane readable.** Oblique angles can introduce a form or establish depth. Turn important text to face the viewer when it must be read.
- **Preserve product truth.** Simplification keeps the real capability, sequence and meaning of the interaction. Where navigation or waiting is omitted, use an editorial cut or dissolve rather than inventing app behavior.

**Shot question:** "What exactly should the viewer notice here?" If the answer includes several unrelated controls, recrop or split the moment into separate beats.

## 4. Timing and spacing

**Why:** Timing is how long a movement takes; spacing is how its speed changes along the way. Easing, offsets and which properties move all express personality. Calm, confident, energetic and playful motion each have their own treatment.

**How:** For a precise, assured SaaS direction, start with compact travel, direct paths, smooth deceleration and clean stops. For a playful app, use more anticipation, elastic response or overshoot where that character belongs.

Inspect the speed through the whole move. In a graph editor, look at the speed curve. In code, plot or step through the eased value frame by frame. Give acceleration and deceleration an intentional shape, and remove accidental hesitations or secondary speed bumps, which usually come from chaining two eases or from keyframes that don't line up.

Two moves of the same duration feel different. A linear move starts and stops abruptly and feels mechanical. An ease-out move covers most of its distance early, then decelerates into a clean stop and feels decisive.

Starting values at 30 fps (double the frame counts at 60 fps):

| Element | Starting duration | Refinement goal |
| --- | --- | --- |
| Main UI panel arrival | 12–18 frames, 0.4–0.6 s | Decisive arrival with a controlled settle |
| Headline entrance | 10–15 frames, 0.33–0.5 s | Quick access to readable text |
| Small confirmation or accent | 6–9 frames, 0.2–0.3 s | Clear feedback with little interruption |
| Offset between related groups | 2–3 frames, about 0.07–0.1 s | A connected sequence |
| Headline hold after settling | 45–75 frames, 1.5–2.5 s | Comfortable first-view reading |

Tune these to travel distance, object size, copy length and brand personality. Bigger, heavier things move slower; small accents move fast. A complex product result may need considerably more reading time.

Useful eases in code:

```js
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const span = (t, a, b) => clamp((t - a) / (b - a));          // progress of t through [a, b]
const easeOut = (k) => 1 - (1 - k) ** 3;                      // decisive arrival
const easeInOut = (k) => (k < 0.5 ? 4 * k ** 3 : 1 - (-2 * k + 2) ** 3 / 2);  // camera moves
const back = (k, s = 1.7) => 1 + (s + 1) * (k - 1) ** 3 + s * (k - 1) ** 2;   // overshoot, for playful moments only
```

## 5. Attention and reading time

**Why:** Motion directs the eye and explains relationships. Overlapping actions keep a sequence connected while preserving a clear hierarchy.

**How:** Give each beat **one dominant event**. Several objects can move, provided they support the same event.

For a product interaction, guide attention through **trigger → response → useful result**.

A starting recipe for a composition reveal, at 30 fps:

- Frame 0: the main panel begins its entrance.
- Frame 3: the headline begins.
- Frame 6: supporting content begins.
- By frame 24: the composition has settled.
- Then hold the useful information long enough to understand it.

Group related content. A few coherent groups give better control than a long cascade of individually animated letters, icons and rows.

**Typography:** Reveal words or lines in meaningful units. Count reading time from the moment the essential text is visible and stable, not from when it starts to enter.

Across the whole film, alternate energetic passages with quieter ones, and give the strongest product payoff a generous moment of stability.

## 6. Transitions that carry the idea

**Why:** Transitions make a film feel continuous. Van Dijk considers the direction and rhythm of the whole sequence when deciding how individual shots connect.

**How:** Design each shot's entry and exit together. Look for an element, direction or shape that can carry the viewer into the next shot. SaaS examples:

- A selected card expands into its detail view.
- A highlighted sentence becomes a task while keeping its recognizable wording.
- A chart's line continues into a brand graphic.
- A collection of items pulls back to reveal the workspace they belong to.

At the handoff, watch the viewer's focal point. Keeping the important element near its previous screen position makes the change easy to follow. When the next shot shows the same subject at another size or place, carry the subject itself there while the rest dissolves around it. A hard cut makes the eye search for it again.

For a first 20-second cut, develop one or two signature transitions and support them with clean cuts or simple reveals. Spend the elaborate transitions where they strengthen the story.

## 7. Depth, lighting and finish

**Why:** Perceived quality depends on small details agreeing with each other. A scene feels carefully built when its surfaces, edges, shadows and movement share one treatment.

**How,** for dimensional UI:

- Establish a clear light direction and carry it through related shots.
- Match shadows to the intended distance between surfaces.
- Keep perspective and layer spacing coherent.
- Use highlights to describe edges and materials.
- Keep sharpness where the viewer reads; put softer detail in supporting areas.

For flat graphics, apply the same discipline to spacing, stroke weight, alignment and edge quality.

Use motion blur deliberately on fast movement, then check that the settled frame has crisp text and controls. Treat grain and texture as part of the visual direction, and check that they survive compression.

**Finish against the delivery file.** Inspect the encoded video for flickering thin lines, banding, rough edges, one-frame jumps, inconsistent scaling and clipped text.

Design vertical or square compositions early when those formats matter, and recompose the hierarchy for each one.

## 8. Sound with the picture

**Why:** Sound gives movement material character, emphasis and resolution. Strip back musical layers to make room for effects, and pick a few standout actions for stronger sound treatment.

**How:** Choose the important sound moments while building the animatic:

- **The initiating action:** a restrained click, tap or tactile cue.
- **The transformation:** a sound that follows the movement's speed and character.
- **The payoff:** a satisfying resolution aligned with the completed result or the brand reveal.

Let quieter supporting sounds connect those moments. Give the effects a shared material character: soft and tactile, clean and digital, or bright and playful.

If there is voice-over, protect its clarity by reducing competing music and effects. The voice either speaks the caption word for word or says something clearly different; a near-paraphrase reads as a mistake. Check the mix on ordinary speakers as well as headphones.

Approve a short sample with finished movement and sound before polishing the whole film. Also watch the sequence muted to confirm the visual story carries the benefit on its own.

## Field-tested defaults

Rules that held up across several produced and critiqued product films. Use them when the project has no studio rules of its own, and break them only on purpose.

**Story**

- Open on real product output from frame 1, and pay off the hook within 2.5 s.
- A number on the first frame needs its subject on the same frame. "446" alone means nothing; "446 Stamps to collect" does.
- Put the film's biggest hit on the moment the feature exists for. Keep that change new at the peak: don't show the after state earlier, for example in a montage.
- Never hold on a state that looks disabled (a grey button, a spinner, a waiting tile) at a moment of tension. The exception is the "before" of the film's one change: hold it about 0.75 s so the viewer has found it before it changes.
- Say or show what the viewer does to cause the change, then hold the result.

**Pace**

- Nothing the viewer must read or count lands faster than an eighth note at the film's tempo. In a long run of items, land the first three at a readable pace and then speed up: the first ones read, the rest read as "many".
- Don't let a new element cover an earlier one before it has had its beat.
- A useful result may hold for more than 2 s. Don't add a new screen just to keep the edit moving.

**Look**

- Avoid the defaults that make films look generic: a centered title on a gradient, everything fading in, corner labels and frame borders, glow on UI chrome, generic particle bursts.
- One display face, one UI face, one accent color unless the brand says otherwise.
- Captions use two sizes and one alignment for the whole film.
- Copy states the benefit, not the spec ("Drops onto anything", not "RGBA"). Numbers must not be misreadable ("~1 MIN", not "1:00").
- Every app window in the film uses one corner radius, large enough to nest around the content's own radius plus its margin.
- The camera trails content as it lands; it never arrives first. A hard cut shows the new shot's content on its first frame; nothing fades in from empty space across a cut. A match cut keeps every element in place across the cut and moves them only after it.
- Energy comes from timing, not effects: land on the beat, push slowly through a shot, punch in on hard cuts. Save camera shake for the one or two biggest hits.
- Hover states don't show on film. Show what the choice leads to.
- Respect platform-owner rules for device frames. Apple's marketing guidelines, for example, forbid cropping, tilting or animating its iPhone imagery, so a stylized app window is often the better container.

**Sound**

- A sound that marks something on screen starts with it or up to 50 ms after, never before.
- Before the payoff: a build, half a beat of silence, then the biggest hit.
- Thin out the music under UI sounds so clicks and typing come through. Duck music and effects about 6 dB under voice-over while the groove keeps moving.
