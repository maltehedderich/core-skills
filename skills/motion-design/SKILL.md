---
name: motion-design
description: "Plan, build, and review short motion-design films for SaaS and app marketing: launch videos, product films, promo and social ad clips, app trailers, and landing-page loops of roughly 6–45 seconds. Develops the brief, promise, storyline, rendered key frames, timed beat sheet, and sound plan first, has them critiqued with fresh eyes, and gets sign-off before any animation, because iterating on a plan is far cheaper than iterating on renders. Then builds the film (following the project's motion studio when one exists, otherwise a code-rendered timeline) and reviews cuts with a scored rubric and prioritized fixes. Use whenever the user wants to make, script, storyboard, animate, render, critique, or fix a product video, motion graphics ad, launch clip, or app promo, even if they only say 'make a video for my app' or share a cut for feedback. Not for UI micro-interactions inside the product itself."
---

# Motion Design

Make short product films (launch videos, promo and social ad clips, app trailers, landing-page loops, roughly 6–45 seconds) that make a SaaS or app product feel desirable and understandable.

A film feels expensive when every frame, movement and sound looks chosen for this product. That comes from exceptional still design, controlled attention, a recognizable motion personality, and enough room to take in the result. This skill covers the whole process: brief, storyline, key frames, timing, sound, production, review and delivery. Its central rule is that the plan has to be excellent before any animation exists.

## Plan before pixels

A plan revision takes minutes. A render-and-review cycle takes an hour or more, and a story problem found in a finished cut usually means rebuilding shots, not adjusting them. The problems that sink most product films are visible long before animation:

- The film proves a secondary feature instead of the one the product leads with.
- Nothing visibly changes, or the change is claimed in text but never shown.
- The payoff is gone before it can be read.
- One composition fills every shot.
- Essential text is unreadable at phone size.

So climb a fidelity ladder, and fix each problem on the cheapest rung where it shows:

| Rung | Artifact | Time to revise | Catches |
| --- | --- | --- | --- |
| 1 | Brief and promise sentence | Seconds | Wrong feature, vague result, wrong audience |
| 2 | Timed beat sheet | Minutes | Missing transformation, late hook, rushed payoff, feature overload |
| 3 | Key frames rendered at full size, checked at viewing size | Minutes | Unreadable text, no hero, incoherent look, monotonous framing |
| 4 | Stills animatic | Minutes | Reading time, pacing, rhythm |
| 5 | One finished 3–5 s sequence | About an hour | Motion character, transitions, sound feel |
| 6 | Full film in every format | Hours per pass | Finish, sync, delivery artifacts |

Rungs 1–4 are the plan. Nothing above rung 4 starts until the plan has passed a fresh-eyes critique and the user has signed off. When a later review finds a problem that belongs to a lower rung (story, framing, timing), go back down: change the plan, check it again, then rebuild. Patching a story problem in animation code produces a polished version of the wrong film.

## Where to start

Match the request to an entry point:

- **A product or idea, and they want a film:** Phases 1–3, the gate, then Phases 4–6.
- **An existing script, storyboard or concept:** treat it as a draft plan. Critique it against the plan-stage rubric, rework it, then go through the gate. Don't faithfully build a weak storyboard; show what you would change and why.
- **Only a plan, script or storyboard:** stop after the gate.
- **A cut to review or fix:** Phase 5. Fixes that change story, framing or timing go back through the plan and the gate before rebuilding. Execution fixes go straight to Phase 4.
- **An explicit request to run end to end without stopping:** still do the full plan and critique, and save the plan. Skip only the wait for approval, and report the plan alongside the film.

## Phase 1: Brief and product truth

Read [planning.md](references/planning.md) before writing the brief.

Find the facts before asking for them. Look for the product's own positioning (landing page hero, App Store listing, README), its real interface and copy, brand tokens (palette, typefaces, corner radius), earlier films and their critiques, and any motion studio rules. Ask the user only what would change the plan: usually the placement and formats, the one action the film should drive, and anything that must or must not appear. State the assumptions you make for the rest.

Write a compact brief:

- **Audience:** who watches, where, and what they already know.
- **Promise:** "[Product] turns [recognizable input or difficulty] into [a valuable, visible result]."
- **Proof:** the one on-screen moment that makes the promise believable.
- **Action:** the one thing the viewer should do next.
- **Personality:** three words for the brand's character, such as precise, calm, assured.
- **Placement:** duration, aspect ratios, whether it autoplays muted, platform overlays.
- **Product truth:** what the product actually does, how long the real action takes, and what the film will omit or compress.

Check the promise against what the product leads with. A beautifully made film about the third-best feature is a common and expensive mistake.

## Phase 2: Storyline

1. **Concept routes.** Sketch two or three routes that differ in idea, not styling: hook, transformation shown, peak, ending, one line each. Pick the one that makes the transformation visible soonest and most convincingly. Keep the others in the plan as one-liners so the user can choose differently.
2. **Signature behavior.** Choose two or three motion verbs that express the transformation (collect, organize, reveal; trigger, propagate, resolve) and define each as a behavior in a motion vocabulary. Reuse them in the demonstration, the transitions and the final brand moment. This is what makes the film feel designed for this product rather than assembled from presets.
3. **Timed beat sheet.** For each beat: time, viewer takeaway, the one dominant event on screen, text or voice-over, sound. Plan reading holds explicitly, place one peak, and mark the one or two signature transitions.

[planning.md](references/planning.md) has the route patterns, beat-sheet rules, time budgets and reading-time arithmetic. [craft.md](references/craft.md) has the craft behind them.

## Phase 3: Key frames, animatic and critique

1. **Key frames.** Fully design the opening, the product payoff and the closing frame as rendered images at full resolution, using the real interface and specific content. Build them in the medium the film will be made in (for a code-rendered film, the film's own page frozen at that time) so the work carries straight into production. Recompose them for every format that matters, such as 9:16 as well as 16:9. Then scale them to real viewing size (about 390 px wide for a phone feed) and measure text sizes instead of eyeballing them. Side by side, the three should already look like one campaign.
2. **Storyboard frames.** Every other beat gets a frame too. These can be rough, but they must exist, because framing variety and the gaze path can only be judged from pictures.
3. **Stills animatic.** Lay the frames on the beat sheet's timings ([planning.md](references/planning.md) has the ffmpeg recipe). The user can feel pacing and reading time in minutes instead of waiting hours for a render.
4. **Fresh-eyes critique.** Have the plan critiqued by a reviewer who did not write it, using the plan-stage rubric in [review.md](references/review.md). If you can start a subagent, give it only the plan, the frames and the rubric, not your reasoning. Otherwise set the plan aside and review it cold, as a stranger would. Builders grade their own work generously: one film whose builder scored it 8/10 on every criterion got 5/10 for hook and readability from a fresh reviewer, who also found that 43% of its length showed an empty form. Revise and review again until no P0 or P1 remains, usually in one to three rounds.

## The gate: sign-off before production

Present the plan and wait for approval. Make it quick to judge:

- The promise sentence and the chosen route, with the alternatives in one line each.
- The beat sheet.
- The key frames (ideally one contact sheet image) and the path to the animatic, which the user can watch at normal speed.
- What the critique changed, and what is still open, especially product-truth questions only the user can answer.
- What production involves: captures, sound, voice, formats, rough effort.

Ask for approval or changes, and iterate here. It is the cheapest point at which to change the film. Production starts only once the user approves.

## Phase 4: Production

Read [production.md](references/production.md).

- **Follow the project's studio when one exists.** Look for a motion studio folder, an AGENTS.md or README with render rules, a render script, or earlier films with briefs and critiques. Its rules override this skill's defaults, because they record what was learned for that brand. Keep the plan where the studio keeps briefs.
- **Otherwise set up a code-rendered film.** Every frame is a pure function of time, captured headless with Playwright and encoded with ffmpeg. [production.md](references/production.md) has the contract and a tested renderer sketch. If the project already uses Remotion, use that.
- **Finish one representative sequence first,** usually the payoff, 3–5 s long, with final typography, curves, overlap, transitions, lighting and sound. It sets the quality bar and the motion rules for everything else. Show it to the user before building the rest, unless they asked for no stops. It is the last cheap moment to change the motion character or the sound.
- **Build the rest against the plan.** The plan is the source of truth. If production reveals a story problem, update the plan and tell the user before rebuilding.
- **Check as you go:** a contact sheet per beat, frame-by-frame steps through every cut and transition, key frames at viewing size, hold durations measured, sound sync and loudness measured.

## Phase 5: Review

Read [review.md](references/review.md). For a video file, also read [footage-intake.md](references/footage-intake.md).

Review every finished cut with fresh eyes before calling it done, preferably by a separate reviewer that steps through the motion frame by frame and does not rely only on a contact sheet. Stills hide easing, flicker and one-frame jumps. Judge comprehension before craft: a first-time viewer, muted and at phone size, should be able to say what the product does, what changed, and what to do next. The output is a verdict, a scorecard and a short prioritized list of fixes, each tagged as plan-level (back through the plan and the gate) or execution-level (fix in production).

## Phase 6: Delivery

- Export every format from its own composition, not as a crop of another.
- Inspect the encoded files, not the source. Look for flickering thin lines, banding in gradients, rough edges, one-frame jumps, inconsistent scaling and clipped text.
- Deliver a cover frame that makes sense without playback, and a muted review copy at viewing size.
- End with the test only a real person can run: show the muted film to someone unfamiliar with the product and ask what it does, what changed, and why they would care. Their answers decide the final revisions.

## Principles

These apply at every phase. [craft.md](references/craft.md) explains each with starting values.

1. **Still frames first.** Composition, hierarchy, color and type set the quality of the film. Each key frame has one visual hero, a deliberate type hierarchy, room around the hero, and the same rules for palette, corners, icon weight, spacing and light.
2. **One visible transformation, one signature behavior.** The viewer sees an input become a result, and the motion verbs that express that change recur across demo, transitions and ending.
3. **Present the interface like product photography.** Use real UI, isolated from distracting chrome. Use specific, plausible content and vary between close, medium and wide framing. Keep text facing the viewer when it must be read. Simplify without changing what the product actually does.
4. **Timing and spacing express character.** Precise and assured means compact travel, direct paths, smooth deceleration and clean stops. Playful earns anticipation and overshoot, on the moments that matter.
5. **One dominant event per beat, and protected reading time.** Guide attention from trigger to response to useful result, count reading time from when text is stable, and give the payoff a generous moment of stillness.
6. **Transitions carry the idea.** Design each shot's entry and exit together, keep the focal point where the eye already is, and spend elaborate transitions only where they strengthen the story.
7. **Internally consistent depth, light and finish,** checked on the encoded file at delivery size.
8. **Sound developed with the picture.** It marks the initiating action, follows the transformation, and lands the payoff, while the film still communicates muted.

## Common mistakes

- Animating before the promise, beat sheet and key frames are settled.
- Effects competing for attention: glow, bounce, blur, camera moves and sound accents all demanding emphasis at once.
- Beautiful but vague: the film never shows what changed, what caused it, or why it helps.
- Rushed reading: the animation uses most of the shot, and the result or call to action disappears before it is understood.
- A feature montage instead of one transformation.
- Trusting your own scores, or judging motion from still frames.
- Fixing a story problem with animation, or speeding a rushed beat up instead of removing information.
- Demo edits that imply capabilities or speed the product does not have.

## Reference files

- [planning.md](references/planning.md): inputs, brief, concept routes, motion vocabulary, beat sheet, key frames, animatic, plan template. Read for Phases 1–3.
- [craft.md](references/craft.md): the eight craft practices in depth, with timing values and field-tested defaults. Read when designing frames, storyline and motion.
- [production.md](references/production.md): studio detection, code-render contract, renderer sketch, sound and voice-over (optionally with the ElevenLabs CLI), self-checks, delivery encoding. Read for Phase 4 and 6.
- [review.md](references/review.md): the rubric for plans and cuts, priorities, output formats, and a brief for a fresh reviewer. Read for the critique in Phase 3 and for Phase 5.
- [footage-intake.md](references/footage-intake.md): ffmpeg commands that turn a video file into frames, cuts, holds and measurements. Read when reviewing a video file.
