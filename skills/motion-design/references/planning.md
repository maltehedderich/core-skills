# Planning a motion film

The plan is rungs 1–4 of the fidelity ladder: brief, beat sheet, key frames and a stills animatic. Everything here is cheap to change, so change it freely. Once the user signs off, the plan becomes the source of truth for production.

## Contents

1. Gather inputs from the project
2. The brief
3. Concept routes
4. Motion vocabulary
5. The beat sheet
6. Key frames
7. Storyboard and stills animatic
8. Plan document template
9. Plan checklist

## 1. Gather inputs from the project

Collect these before asking the user anything:

- **Positioning.** The landing page hero, the App Store or Play listing (title, subtitle, first screenshot), the README. Note the lead claim. The film should normally prove that claim and not a secondary feature.
- **Real interface.** Run the app or capture its screens (Playwright for web apps, the simulator for iOS). Find the design tokens (CSS variables, Tailwind config, DESIGN.md), fonts, icon set, corner radius and logo files.
- **Real content.** Plausible, specific sample data in the product's own vocabulary. Never "Project 1" or lorem ipsum.
- **Earlier films.** Briefs, critiques and studio rules record what already failed. Read them before repeating it.
- **Placement.** Platforms, aspect ratios, duration limits, muted autoplay, the platform's current overlay template and safe zones, and how the call to action is delivered (a platform button or the film's own end card).

Ask only when the answer changes the plan. When placement is unstated, assume 20 s, 16:9 plus 9:16, muted-first, and the site's primary call to action, and say so.

## 2. The brief

```markdown
- Audience: <who, where they watch, what they already know>
- Promise: <Product> turns <recognizable input or difficulty> into <valuable, visible result>.
- Proof: <the one on-screen moment that makes it believable>
- Action: <the one next step>
- Personality: <three words>
- Placement: <duration, formats, muted or not, overlays>
- Product truth: <what it really does, how long it really takes, what the film omits or compresses>
```

Test the promise before going further:

- Would this audience recognize the input without explanation?
- Can you point at the result in a frame? A result that only exists in a caption is a claim, not proof.
- Is it the transformation the product leads with? If not, write down why this one was chosen.
- Can it be shown as one continuous chain within the duration?
- For each claim the film will make visually, how is it verified (a real capture, the code path, the listing)? List every omission, such as skipped loading or navigation, and make sure none implies speed or capability the product lacks.

## 3. Concept routes

Write two or three routes that differ in idea. Patterns that work for product films:

- **Result first.** Open on the desirable result, show where it came from, return to it.
- **Problem, turn, result.** Open on a recognizable difficulty; one action turns it; hold the result.
- **Plenty, taken away, earned back.** Show what is possible, take it away ("none of this is yours yet"), earn it back through the product.
- **Against the clock.** A visible counter or side-by-side makes a speed claim concrete. Use it only when the claim is true.
- **One thing, transformed.** Track one recognizable piece of content (a sentence, a photo, a row) as it becomes the result, so it stays identifiable throughout.

For each route, write one line each for hook (frame 1), transformation shown, peak, ending, and motion verbs. Choose the route that makes the transformation visible soonest, gives the most convincing proof, suits the personality, and can be built from the real UI. Record the runners-up in one line each.

## 4. Motion vocabulary

Derive two or three verbs from the transformation. Automation might be trigger, propagate, resolve. Collaboration might be gather, align, advance. Analytics might be collect, organize, reveal. Define each as a behavior, and add the plain actions every film needs:

| Action | Behavior: easing, duration, distance, sound | Used for |
| --- | --- | --- |
| Collect | Items travel on direct paths into one group, ease-out, 0.4 s, 2-frame offsets, soft tick per arrival | Gathering inputs; the end card |
| Reveal | The result scales from 96% to 100% with a 0.3 s ease-out; nothing else moves | The payoff |
| Enter | 12–24 px travel, 0.4–0.5 s ease-out | Headlines, panels |
| Settle | Clean stop, no rebound | Everything that must be read |
| Cut | Hard cut, new content complete on its first frame | Between unrelated views |

Each verb means one thing. If the same movement is used for two different meanings, the viewer stops being able to read it.

Match the behavior to the personality:

- **Precise, assured:** compact travel, direct paths, smooth deceleration, clean stops.
- **Calm:** smaller distances, longer and softer eases, fewer simultaneous moves.
- **Energetic:** faster moves, cuts on the beat, punch-ins on hard cuts.
- **Playful:** anticipation, elastic response and overshoot, kept for meaningful moments.

## 5. The beat sheet

```markdown
| Time | Viewer takeaway | Picture: the one dominant event | Text / VO | Sound |
| --- | --- | --- | --- | --- |
| 0–2 s | ... | ... | ... | ... |
```

Rules for a strong beat sheet:

- Frame 1 has a clear subject and a credible reason to care. The hook pays off within about 2.5 s.
- Setup is short. An empty form, loading state or blank canvas gets 0.5 s or a quick punch-in, not a beat.
- The demonstration and its result get most of the running time.
- Each beat has one dominant event. Other movement supports it.
- Product interactions read as trigger, then response, then useful result, in one consistent framing.
- There is one peak. It gets the biggest image and the biggest sound, and it holds still long enough to read (start at 1.25 s or more, with all motion stopped within 0.2 s of the hit).
- Reading holds are planned, not left over. Count from the moment the text is stable. Starting rule: read the text aloud at a normal pace, then add a beat. Keep at least 1.2 s after the last word lands, and 1.5–2.5 s for a short headline. A complex result needs more.
- No full-frame title card under 1 s. A step title works better as a caption that stays over the UI.
- Consecutive beats change scale, ground or composition: close for the action, medium for its response, wide for the resulting workflow. One composition for the whole film reads as a slideshow.
- The same information stays identifiable through the sequence. That continuity is what makes the demo convincing.
- One or two signature transitions carry the idea. Clean cuts or simple reveals do the rest.
- Energetic passages alternate with quieter ones.
- The ending keeps the demonstrated result in frame beside the product name and one call to action. For a landing-page loop, the result settles and the last frame matches the first.

Starting budgets, to adjust:

| Duration | Hook | Source or setup | Transformation | Result | Ending |
| --- | --- | --- | --- | --- | --- |
| 15 s | 0–2 s | 2–4 s | 4–9 s | 9–12 s | 12–15 s |
| 20 s | 0–2 s | 2–5 s | 5–11 s | 11–16 s | 16–20 s |
| 30 s | 0–3 s | 3–7 s | 7–18 s | 18–25 s | 25–30 s |

With music, pick a tempo early (110–130 BPM suits most product edits) and plan cuts and hits on the beat grid, so the beat sheet's times are already musical. At 120 BPM a beat is 0.5 s.

Example, a 20 s film for a meeting-notes app that supports these actions:

| Time | What to show | Purpose |
| --- | --- | --- |
| 0–2 s | A clear task list and the promise "Turn meetings into action" | Establish the desirable result |
| 2–5 s | A meeting note containing a recognizable decision | Show the source |
| 5–11 s | That decision becomes tasks with owners and dates | Demonstrate the transformation |
| 11–16 s | Follow one task into the team's board; settle on the result | Make the benefit concrete |
| 16–20 s | Product name, benefit and one clear call to action | Finish with recognition and direction |

## 6. Key frames

Design three frames fully: the opening, the product payoff and the closing frame. Add the action frame when the trigger is small or subtle.

**Build them for real.** Use the medium the film will be produced in. In a code-rendered film, a key frame is the film's page frozen at that time, rendered to PNG at full resolution, so nothing is thrown away when animation starts. Use real captures and real copy. Rebuild any text the viewer must read as live type: a screenshot enlarged in the film turns soft. Remove browser chrome, notifications and unrelated content. Crop on real edges (a container's edge or the gutter between elements), never through content.

**Design each frame:**

- One visual hero, with the strongest combination of size, contrast and position.
- A deliberate type system. Start with one family (or one display face plus one UI face), two weights, and distinct sizes for headline, supporting copy and UI. Refine line breaks, spacing and optical alignment.
- Room around the hero. Quieter background wherever the viewer has to read.
- Consistent rules across all frames: palette, corner treatment, icon weight, spacing logic, light direction.

**Recompose for each format.** A 9:16 frame needs its own hierarchy, not a crop of the 16:9. Keep essential text and product detail inside the platform's current safe zone, but centre the composition on the frame itself, because the film also plays without the overlay.

**Measure at viewing size.** Scale each frame to the width it will really be seen at (about 390 px for a phone feed, or the embed's rendered width) and check that everything essential still reads. Field-tested sizes for feed video: at 1080 px frame width, focal text 80 px or larger and nothing the viewer must read under 50 px; at 1920 px width, about 142 px and 89 px. Measure in the source and write the numbers into the plan.

```sh
# One frame at phone-feed width
ffmpeg -v error -i opening.png -vf "scale=390:-2" opening-390.png

# Campaign test: the three key frames side by side at viewing width
ffmpeg -v error -i opening.png -i payoff.png -i closing.png -filter_complex \
  "[0]scale=390:-2[a];[1]scale=390:-2[b];[2]scale=390:-2[c];[a][b][c]hstack=inputs=3" key-frames-390.png
```

Practical test: at viewing size, the three frames side by side should already look like one coherent campaign.

## 7. Storyboard and stills animatic

Give every remaining beat a storyboard frame. Rough is fine: real captures in position, blocks for graphics, the caption at its real size. Put all frames on one contact sheet with their times to check framing variety and the gaze path across beats. The eye should be able to travel from beat to beat without hunting.

Then lay the frames on the beat sheet's timings. Write `beats.tsv` with one `image seconds` pair per line, in order, all images the same size:

```sh
args=(); n=0
while read -r img dur; do args+=(-loop 1 -t "$dur" -i "$img"); n=$((n + 1)); done < beats.tsv
ffmpeg -y -v error "${args[@]}" -filter_complex "concat=n=$n:v=1:a=0,fps=30,format=yuv420p" -c:v libx264 animatic.mp4
```

To hear the tempo against the cuts, add a click track (here 120 BPM for 20 s):

```sh
ffmpeg -y -v error -f lavfi -i "aevalsrc='0.5*sin(2*PI*1000*t)*lt(mod(t,60/120),0.03)':s=48000:d=20" click.wav
ffmpeg -y -v error -i animatic.mp4 -i click.wav -c:v copy -c:a aac -shortest animatic-click.mp4
```

The user can watch the animatic at normal speed. You cannot watch in real time, so review it through the beat sheet's holds and the contact sheet, and say so.

## 8. Plan document template

Save the plan as Markdown where the project keeps film briefs (for example `films/<film>/brief.md`), or next to the film if there is no convention.

```markdown
# <Film name> plan

**Status:** draft | critiqued, round N | approved on YYYY-MM-DD

## Brief
Audience, promise, proof, action, personality, placement.

## Routes considered
The chosen route and why; the others in one line each.

## Storyline
The beat sheet, with times, takeaways, the dominant event, text or VO, and sound.

## Key frames
For opening, payoff and closing in each format: image path, what the viewer should notice, measured text sizes at viewing size.

## Motion vocabulary
Action | behavior | used for. Signature transitions and where they happen.

## Look
Palette, typefaces and sizes, grid and safe zones, light direction, texture.

## Sound
Tempo or track, the initiating, transformation and payoff sounds, VO script, how it reads muted.

## Product truth
Each visual claim and how it was verified; every omission or compression and why it is honest.

## Production
Captures and assets needed, tools, which 3–5 s sequence will be finished first.

## Acceptance
What a first-time, muted viewer should be able to say afterwards.

## Critique log
Round, reviewer verdict, what changed.
```

## 9. Plan checklist

The plan is ready for the gate when:

1. The promise sentence names a recognizable input and a visible result, and matches what the product leads with, or the plan says why not.
2. Frame 1 has a subject and a reason to care, and the hook pays off within about 2.5 s.
3. The transformation is shown, not claimed, as trigger, response and useful result.
4. Every beat has one dominant event, and the same information stays identifiable from source to result.
5. There is one peak, held still long enough to read.
6. Every piece of text has a planned hold that passes the read-aloud test.
7. Key frames exist as rendered images in every format, with measured text sizes that pass at viewing size, and they look like one campaign.
8. Framing changes from beat to beat. No single composition carries the film.
9. The motion vocabulary defines two or three signature verbs, and one or two signature transitions are placed.
10. The sound plan names the initiating, transformation and payoff moments, and the film still makes sense muted.
11. The ending shows the result beside the product name and one action, or the loop seam is planned.
12. Every visual claim is verified or listed as an open question for the user.
13. A fresh reviewer has found no open P0 or P1.
