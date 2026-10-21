# Motion Design

Motion Design helps an assistant plan, build and review short marketing films for SaaS products and apps: launch videos, promo and social ad clips, app trailers and landing-page loops of roughly 6–45 seconds.

Use it when you want a product film that makes one valuable change easy to understand, or when you want an existing cut critiqued and fixed.

## Install the Skill

From the repository root:

```sh
./coreskills install --tool claude --skills motion-design
```

Replace `claude` with `codex`, `copilot`, or `gemini` when you use a different tool.

## Make a Film

Ask your assistant to use the skill from the product's repository, so it can use the real interface, copy and brand assets:

```text
/motion-design Make a 20-second launch film for this app, for LinkedIn and the landing page.
```

To review a cut instead:

```text
/motion-design Review films/out/launch-9x16.mp4. It's a YouTube Shorts ad for US iPhone users.
```

## How It Works

The skill puts the plan first, because a plan revision takes minutes and a render-and-review cycle takes hours.

| Step | What you get |
| --- | --- |
| Brief | Audience, a one-sentence promise ("[Product] turns [input] into [visible result]"), proof, action, personality and placement, checked against what the product actually does. |
| Storyline | Two or three concept routes, a motion vocabulary built on the product's own verbs, and a timed beat sheet. |
| Key frames and animatic | Opening, payoff and closing frames rendered at full size and checked at phone size, plus a stills animatic you can watch at normal speed. |
| Critique and sign-off | A fresh-eyes review of the plan, then a stop for your approval before any animation. |
| Production | The film built with your project's motion studio rules, or as a code-rendered timeline (HTML, Playwright and ffmpeg) when there is none, starting with one finished 3–5 s sequence. |
| Review and delivery | A scored review of the cut with prioritized fixes, every format composed for its own frame, a cover frame, and a muted review copy for a first-time-viewer test. |

Fixes that change the story go back through the plan instead of being patched in animation.

## References

| File | Covers |
| --- | --- |
| [`planning.md`](references/planning.md) | Brief, concept routes, motion vocabulary, beat sheet, key frames, animatic, plan template and checklist. |
| [`craft.md`](references/craft.md) | Key frames, transformation, interface presentation, timing and spacing, attention, transitions, finish and sound, with starting values. |
| [`production.md`](references/production.md) | Studio detection, the render contract, a renderer sketch, captures, sound, self-checks and delivery. |
| [`review.md`](references/review.md) | The R1–R10 rubric for plans and cuts, priorities, output formats and a brief for a fresh reviewer. |
| [`footage-intake.md`](references/footage-intake.md) | ffmpeg commands for frames, cuts, holds, silence, viewing size and loop seams. |

## Requirements

Planning needs nothing beyond the assistant. Rendering key frames, animatics and films needs ffmpeg, and the code-rendered route also needs Node with Playwright's Chromium. For a synthesized voice-over, the skill can use the [ElevenLabs CLI](https://github.com/elevenlabs/cli) (`brew install elevenlabs/tap/elevenlabs`, then `elevenlabs auth login`); it asks before relying on it.
