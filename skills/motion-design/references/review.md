# Reviewing plans and cuts

One rubric serves both the plan critique before production (Phase 3) and the review of a cut (Phase 5). At plan stage you judge from the brief, the beat sheet, rendered key frames and the animatic. At cut stage you judge from the video itself.

## Contents

1. Stance
2. Inputs
3. Workflow
4. The rubric
5. Priorities
6. Output formats
7. Brief for a fresh reviewer
8. Quality checks
9. Failure modes

## 1. Stance

Comprehension before craft. A polished film whose result vanishes before it can be read fails. A rough animatic with a clear promise, visible proof and one point of attention per beat is ready for polish. Every recommendation should move the film closer to a first-time viewer answering three questions with the sound off:

1. What does it do?
2. What changed?
3. What would I do next?

Judge as that viewer, at real viewing size, muted first. Knowing the product is not evidence that the film is clear.

## 2. Inputs

Gather what the material does not already reveal. Infer the rest and state your assumptions. Never hold a review back for brand guidelines or analytics.

- **Material:** the plan document and key frames, an animatic, a video file, exported frames, a script or a written concept.
- **Stage:** plan, animatic, representative sequence, rough cut or final. The stage decides which fixes are cheap.
- **Placement:** platform, aspect ratio, duration, muted autoplay or not. 9:16 suggests a vertical feed; a silent 16:9 loop on a page suggests a landing-page loop.
- **Intent:** the brief's promise, audience and action, if one exists.
- **Product truth:** what the product actually does and how long it takes, so the demo can be checked for honesty.
- **Evidence:** retention graphs, comprehension tests, earlier critiques.

For a video file, run [footage-intake.md](footage-intake.md) first and build a beat map before judging anything:

| Time | Beat | On screen | On-screen text | Primary focus | Audio / VO |
| --- | --- | --- | --- | --- | --- |

## 3. Workflow

1. **Reconstruct the promise.** Write the transformation the material actually communicates, from the material alone: "[Product] turns [input] into [result]." Compare it with the intended one. A gap here, such as a vague result or three capabilities competing, is usually the root cause of findings further down, so name it first.
2. **First-viewing check.** Walk the beats muted and answer the three questions with the time each answer first becomes clear, or `unclear`. Then freeze the first frame: is there a clear subject and a credible reason to care? Label this an expert simulation; it does not replace a real first-time viewer.
3. **Score the rubric,** citing evidence for every score.
4. **Prioritize fixes** and tag each as plan-level or execution-level.
5. **Revise the structure** when fixes reorder beats, cut a feature or move time: give a revised beat sheet.
6. **Plan validation:** the smallest test that would confirm the top fixes.

## 4. The rubric

Score each criterion 0–3 and cite a timestamp, frame or plan line. Use `n/a` with a reason when the material cannot support a judgment: sampled frames cannot show easing, a beat sheet cannot show legibility, a muted file cannot show sound.

| Score | Meaning |
| --- | --- |
| 0 | Missing, or working against the film's goal |
| 1 | Present but unclear; a first-time viewer would likely miss it |
| 2 | Works, with friction that slows comprehension or weakens impact |
| 3 | Clear and deliberate; hard to improve without changing the concept |

| Criterion | Question | At plan stage, judge from | At cut stage, look for |
| --- | --- | --- | --- |
| **R1 Promise** | Is the film built on one specific, valuable, visible transformation, the one the product leads with, and true to the product? | The promise sentence, routes, product-truth notes | Can the transformation sentence be written from the film alone, and does it match the intent? Feature montage, claimed-but-unshown results, implied speed or capability |
| **R2 Opening** | Do frame 1 and the first beat give the intended viewer a reason to keep watching? | Opening key frame, first two beats | Frozen first frame: clear subject, credible reason to care; hook paid off within about 2.5 s; no logo reveal or abstract build-up filling the opening |
| **R3 Frames** | Does each key frame have one hero, a deliberate type hierarchy, room, consistent rules, and legibility at viewing size in every format? | Rendered key frames scaled to viewing width, measured text sizes, the campaign test | Key frames at viewing size, text sizes, safe zones, native composition per format, consistency across shots |
| **R4 Product proof** | Is the interface presented like product photography and does it prove the promise? | Planned shots, captures, sample content, framing plan | Real UI isolated from chrome; specific content; close, medium and wide framing; readable information plane; visible cause and effect; honest edits |
| **R5 Attention and holds** | Does each beat have one dominant event, and does every important moment hold long enough? | Beat sheet: dominant event per beat, planned holds against the read-aloud test, the peak's stillness | A single gaze path; trigger, response, result; measured holds; the payoff stable; energetic and quiet passages alternating |
| **R6 Motion character** | Do timing and spacing express the brand, through a consistent signature vocabulary? | Motion vocabulary: verbs, behaviors, personality fit | Frame strips through moves: intentional acceleration and deceleration, no accidental speed bumps, verbs used consistently, no preset look |
| **R7 Transitions** | Do transitions carry the idea and keep the focal point continuous? | Planned signature transitions and how each shot exits and enters | Frames either side of every cut: subject carried or kept in place, hard cuts complete on their first frame, nothing hunting for the eye |
| **R8 Finish** | Are depth, light, edges and texture internally consistent, and does the encoded file hold up? | Look section: light direction, shadow logic, texture; usually `n/a` otherwise | Light and shadow agreement, crisp settled text, motion blur only on fast moves, banding, flicker, clipped text, scaling jumps |
| **R9 Sound** | Does sound mark the initiating action, transformation and payoff, and does the film still work muted? | Sound plan and VO script against the beat sheet | Measured sync, silence before the peak, VO clarity and ducking, the key claim not existing only in VO. Sound you could not hear is `n/a` |
| **R10 Ending** | Does the ending do what the placement needs? | Closing key frame | Ad or launch: result still visible beside the product name and one clear action. Landing-page loop: result settles and the seam is invisible |

## 5. Priorities

Write each finding as: where (timestamp, frame or plan line), criterion, observed problem, which viewer question it blocks, the concrete fix with rough amounts, its level, and effort (`S`, `M` or `L` at the current stage).

- **P0, fix before anything else:** a first-time viewer cannot answer one of the three questions; the film proves the wrong feature; the opening gives no reason to watch; essential text or the result is unreadable or hidden by platform UI; the demo misrepresents the product.
- **P1, fix in this revision:** the answers arrive late, compete for attention or don't hold long enough; framing never changes; the ending is weak or split; muted comprehension depends on the voice-over.
- **P2, polish once comprehension holds:** easing, vocabulary consistency, transition craft, finish, sound design.

Tag every fix:

- **Plan-level:** changes the promise, route, beats, framing, holds or key frames. Update the plan, check it again, and get sign-off before rebuilding.
- **Execution-level:** the plan is right and the build missed it. Fix it in production.

Rank within a tier by leverage: root causes before symptoms, earlier before later (viewers who leave in the opening never see a fix at second 12), cheap before expensive at the current stage. Fix pacing by removing information before speeding anything up.

Adjust to the stage. At plan stage, structural change is cheap, so push hard on promise, opening, proof and frames. At animatic or rough cut, fix composition, attention and holds before anyone polishes. On a locked final, prefer edit-level fixes (trim, re-time, extend a hold, reframe, reorder, swap the end card, add captions) and carry deeper problems into the next film, but still name an expensive P0 honestly.

Keep the list short: every P0, the strongest P1s (usually five or fewer), and at most three P2s. If any P0 is open, say plainly that polish should wait.

## 6. Output formats

### Plan critique

1. **Reviewed:** material, stage, assumptions.
2. **Verdict:** `Rethink the concept` (no single visible transformation), `Rework the storyline` (right promise, wrong beats), `Fix frames and timing` (story holds; frames or holds fail), or `Ready for sign-off`.
3. **Promise check:** as written, as the beats actually deliver it, and sharpened if needed.
4. **First-viewing check** from the animatic or beat sheet, labeled a simulation.
5. **Keep:** up to three strengths.
6. **Scorecard:** `criterion | score | evidence`, with `n/a` where the plan cannot show it.
7. **Prioritized fixes,** P0 first.
8. **Check in production:** risks the plan cannot settle, such as easing feel or audible sound.

### Cut review

1. **Reviewed:** material, stage, placement, aspect ratio, duration; what could and could not be assessed; assumptions.
2. **Verdict:** `Rethink the concept`, `Fix comprehension first` (at least one P0), `Tighten before polish` (no P0, P1s slow comprehension), or `Polish and test`. One or two sentences on why.
3. **Promise check:** communicated beside intended.
4. **First-viewing check:** the three questions with answers and times, plus the first-frame verdict, labeled a simulation.
5. **Keep:** up to three strengths the revision must not lose.
6. **Scorecard:** `criterion | score | evidence` for R1–R10.
7. **Prioritized improvements,** numbered, P0 first, each in this shape:

   `1. P0 · 0:00–0:02 · R2 Opening · plan-level` What is wrong, as observed. **Fix:** the concrete change. **Unblocks:** which viewer question or criterion. **Effort:** S.

8. **Revised beat sheet,** only when the structure changes: `time | viewer takeaway | visual action`, labeled as starting points.
9. **Validation:** the next test and the result that would confirm the fixes. Usually: show the revised cut once, muted at viewing size, to someone unfamiliar with the product, and ask what it does, what changed and what they would do next. If the opening is the main doubt, cut two opening variants and hold everything else constant. A replay spike or strong retention alone does not show the message landed.

## 7. Brief for a fresh reviewer

Builders grade their own work generously, so the critique should come from a reviewer who did not make the material. With a subagent tool, start one with this brief and nothing else from the build conversation:

```text
You are a senior motion designer reviewing a <plan | cut> of a <duration> <placement> film for <product>.
You have not seen it before. Material: <paths to plan, key frames, animatic or video>.
Intended promise, audience and action: <from the brief, if any>.
Read <path>/references/review.md and use its rubric and output format<; for a video, first run the commands in references/footage-intake.md>.
Judge as a first-time viewer, muted, at <viewing width> px. For motion, step through frames at 10 fps or more around cuts and moves; don't judge motion from a contact sheet.
Don't soften scores. The builder's own scores are not evidence.
Return the verdict, scorecard and prioritized fixes, each tagged plan-level or execution-level.
```

Without a subagent, finish the build, set your notes aside, and review only the artifacts, in this order: first frame, key frames at viewing size, the beat map, then motion.

## 8. Quality checks

A review is ready when:

1. The promise is written down both as communicated and as intended.
2. The three viewer questions are answered with times, or marked `unclear`.
3. Every score cites evidence, and unassessable criteria are `n/a` with a reason.
4. No P2 outranks an open P0 or P1.
5. Every fix names a location, an executable change and its level.
6. Pacing fixes remove information before speeding things up.
7. Fixes fit the stage and the placement.
8. Product-honesty concerns are raised, or their absence is stated.
9. The list is short enough to act on in one revision.
10. Strengths worth keeping are named.
11. It ends with a concrete validation step.
12. Nothing is invented: no fabricated data, quotes, or claims about motion or audio you did not observe.

## 9. Failure modes

- Leading with easing, transitions or color while the result disappears before it can be read.
- Reviewing as someone who already knows the product.
- Rewarding a feature montage because every screen looks polished.
- Prescribing "speed it up" for a rushed beat instead of removing information.
- Notes like "make it pop", "pacing feels off" or "more dynamic" with no time and no fix.
- Judging easing from sampled frames, or sound from a muted file, without saying so.
- Asking for a rebuild of a locked final when a re-time, crop, hold or caption would do.
- Asking for more features, text or scenes in a film whose problem is overload.
- Accepting demo edits that imply capabilities or speed the product does not have.
- Patching a plan-level problem in production instead of sending it back through the plan.
- A long list of equal-weight notes.
