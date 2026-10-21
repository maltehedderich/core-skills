# Producing the film

Production starts after the user approves the plan. The plan stays the source of truth: when a production finding changes the story, framing or timing, update the plan first and tell the user.

## Contents

1. Use the project's studio when it has one
2. Otherwise, set up a code-rendered film
3. Build order
4. Sound and voice
5. Self-checks while building
6. Delivery

## 1. Use the project's studio when it has one

Look for:

- a `motion-studio/`, `motion/`, `video/` or `films/` folder;
- an AGENTS.md, CLAUDE.md or README that describes render rules;
- a render script (`render.mjs`, `remotion.config.ts`, a Makefile target) or a Remotion, Motion Canvas or Lottie setup in `package.json`;
- earlier films with briefs, cues, critiques or review notes.

When you find one, read its rules and at least one earlier film's brief and critique before writing code. The studio's rules override this skill's defaults: they record what went wrong for this brand before. Put the plan where the studio keeps briefs, use its asset layout and tooling, and render the way it renders. When a critique of the new film finds a problem that is not specific to its story, suggest adding the fix to the studio's rules.

## 2. Otherwise, set up a code-rendered film

Ask where it should live if that is not obvious. A `motion-studio/` folder in the product repository works well, because the film can use the product's real assets and tokens.

Tools: Node with Playwright (`npm i -D playwright && npx playwright install chromium`) and ffmpeg. If the project already uses Remotion, use Remotion and keep the same contract through `useCurrentFrame()`.

### The render contract

Every frame is a pure function of time. The film page exposes `window.seek(t)`, which paints the frame at time `t`, and the renderer screenshots one frame after another.

- No CSS transitions or animations, no `setTimeout`, no `requestAnimationFrame` in render mode, and no state carried from one frame to the next. Any frame must render correctly from a fresh seek.
- Seeded randomness only, never `Math.random()`, so the same frame always produces the same pixels.
- Load everything before the first frame: fonts, images, captured video frames. Expose a `window.ready` promise.
- Put every hard cut on a frame time, or a frame will show both shots.
- A CSS background or mask image may still be loading after a fresh seek. Draw images that must appear with `<img>` elements that `window.ready` waits for.

A minimal film page:

```html
<!doctype html>
<html><head><meta charset="utf-8">
<style>
  html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; background: #f6f3ee; font-family: system-ui, sans-serif; }
  #hero { position: absolute; left: 50%; top: 50%; translate: -50% -50%; font-size: 120px; font-weight: 700; color: #1b2440; }
</style></head>
<body><div id="hero">Ready</div>
<script type="module">
const DURATION = 2;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const span = (t, a, b) => clamp((t - a) / (b - a));       // 0 before a, 1 after b
const easeOut = (k) => 1 - (1 - k) ** 3;
const hero = document.getElementById('hero');

// Paint frame t. Every property comes from t alone; nothing carries over from the previous frame.
function paint(t) {
  const k = easeOut(span(t, 0.2, 0.7));
  hero.style.transform = `translateY(${(1 - k) * 60}px)`;
  hero.style.opacity = k;
}

window.DURATION = DURATION;
window.seek = paint;
window.ready = Promise.all([document.fonts.ready, ...[...document.images].map((img) => img.decode())]);
window.seek(Number(new URLSearchParams(location.search).get('t') ?? 0));   // ?t=1.5 previews a frame
</script></body></html>
```

Read `innerWidth` and `innerHeight` to compose each format from the same timeline, with its own layout per aspect ratio rather than a crop.

A minimal renderer, which also renders single key frames:

```js
// node render.mjs film.html out.mp4 [--size 1920x1080] [--fps 30]
// node render.mjs film.html still.png --at 12.5 [--size 1080x1920]
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import path from 'node:path';

const [file, out] = process.argv.slice(2);
const opt = (name, fallback) => { const i = process.argv.indexOf(`--${name}`); return i > 0 ? process.argv[i + 1] : fallback; };
const [width, height] = opt('size', '1920x1080').split('x').map(Number);
const fps = Number(opt('fps', 30));

const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none', '--hide-scrollbars'] });
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
page.on('pageerror', (e) => { console.error(e); process.exit(1); });
await page.goto('file://' + path.resolve(file));   // serve over http instead if the film uses fetch()
await page.evaluate(() => window.ready);

if (out.endsWith('.png')) {
  await page.evaluate((t) => window.seek(t), Number(opt('at', 0)));
  await page.screenshot({ path: out });
} else {
  const duration = await page.evaluate(() => window.DURATION);
  const ffmpeg = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'slow', '-movflags', '+faststart', out],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let frame = 0; frame < Math.round(duration * fps); frame++) {
    await page.evaluate((t) => window.seek(t), frame / fps);
    if (!ffmpeg.stdin.write(await page.screenshot())) await once(ffmpeg.stdin, 'drain');
  }
  ffmpeg.stdin.end();
  await once(ffmpeg, 'close');
}
await browser.close();
```

Grow it as the film needs: a static server for `fetch()`, several pages in parallel, subframe accumulation for motion blur, muxing the soundtrack, a draft mode with a fast preset. Keep the contract.

Suggested layout per film: `films/<film>/` holds the plan (`brief.md`), `index.html`, cue and beat data, score code and critiques. Large media (captures, renders) go in an ignored folder or the project's asset store.

### Captures

- Capture the real product at the size the film will show it, at default text size, in a clean account with specific sample data. Script captures (Playwright for web, XCUITest or simulator recordings for iOS) so they can be redone after a product change.
- Check recorded frame times around every planned cut. Screen recordings drop and bunch frames during heavy transitions; cut past a gap rather than hold a half-faded frame.
- Rebuild text the viewer must read as live type in the film page rather than zooming a screenshot.

## 3. Build order

1. **Key frames** already exist from the plan. Make them the film's page frozen at their times if they are not yet.
2. **The representative sequence.** Finish one 3–5 s stretch, usually the payoff, with final typography, curves, overlap, transitions, lighting and sound. Check it frame by frame (see self-checks). Write down the motion rules it establishes, and add them to the plan's motion vocabulary. Show it to the user before building the rest unless they asked for no stops.
3. **The rest of the film,** beat by beat against the beat sheet, reusing the vocabulary.
4. **Every format,** each composed for its own frame.
5. **Final render** with full quality settings, only after the self-checks pass.

## 4. Sound and voice

- **Music.** A supplied or licensed track is best. Without one, a score can be synthesized in code (Web Audio's `OfflineAudioContext`, or Python with numpy) on the film's beat grid. Measure the beat grid of a supplied track and put cuts and hits on it.
- **Effects.** Mark the three planned moments (initiating action, transformation, payoff) and connect them with quieter supporting sounds of the same material. A sound that marks something on screen starts with it or up to 50 ms after.
- **Voice-over.** Only when the user wants one; the film should still work muted. Use a supplied recording, or a text-to-speech tool or skill when one is available. Generate one take of the whole script, or one request per line when a single line must be redone. Place lines by word timings (forced alignment) rather than by ear, and duck music and effects about 6 dB underneath. Listen-dependent judgments such as tone and pitch need a human; say so.
- **ElevenLabs (optional).** For a synthesized voice-over, the ElevenLabs CLI covers voice search, text-to-speech and forced alignment. Offer it when the user wants a voice-over and has nothing better in place. Check `elevenlabs auth status` first. If the command is missing or not signed in, ask the user to set it up themselves, because login opens a browser and uses their account:

  ```sh
  brew install elevenlabs/tap/elevenlabs   # macOS; other platforms: https://github.com/elevenlabs/cli
  elevenlabs auth login                    # or set ELEVENLABS_API_KEY
  ```

  Once it works, pick a voice that fits the brief's personality words, then generate and align each take:

  ```sh
  elevenlabs voices search --human
  elevenlabs models list --human
  elevenlabs text-to-speech convert --voice-id <voice> --model-id <model> --output-format mp3_44100_192 \
    --text 'Turn meetings into action.' -o vo/take-1.mp3
  elevenlabs forced-alignment create --file vo/take-1.mp3 --text 'Turn meetings into action.' > vo/take-1.align.json
  ```

  Record the voice, model and settings in the plan so a line can be redone in the same voice. Generation spends the user's ElevenLabs credits, so generate a few takes, not dozens.
- **Mix and loudness.** Most social and web platforms normalize to around −14 LUFS integrated. Master near that, or to the studio's own target, with true peak at −1 dBTP or lower. Measure on the final master:

```sh
ffmpeg -hide_banner -nostats -i film.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E '^\s+(I|Peak):'
```

Mux audio onto a rendered picture:

```sh
ffmpeg -y -v error -i picture.mp4 -i mix.wav -c:v copy -c:a aac -b:a 192k -shortest film.mp4
```

## 5. Self-checks while building

- **Contact sheet per beat.** Render one frame per beat (or per second) and look at the sheet for gaze path, framing variety and consistency.
- **Step through motion.** Render every frame of each cut, transition, landing and push as a strip, and check for one-frame jumps, slivers, elements arriving before the camera, and accidental speed bumps. [footage-intake.md](footage-intake.md) has the commands.
- **Viewing size.** Scale key frames and the payoff hold to viewing width and check that everything essential reads.
- **Holds.** Measure how long each piece of text and the result stay still, and compare with the plan.
- **Sync.** Compare sound onsets with the frames they mark.
- **Self-scores are optimistic.** Use the rubric in [review.md](review.md) to find problems, not to declare the film finished. The finished cut gets a fresh-eyes review in Phase 5.

## 6. Delivery

- **Encode:** H.264, `yuv420p`, CRF 16–18, `+faststart`, AAC at 48 kHz. 30 fps suits most product films; 60 fps helps fast UI motion. Check the platform's current upload specs for size and duration limits.
- **Formats:** a master per aspect ratio (commonly 16:9, 1:1, 9:16), each composed for its frame.
- **Cover frame:** a still that makes sense without playback, usually the complete hook or the payoff.
- **Review copies:** a muted copy scaled to viewing width (`scale=390:-2` for a phone feed), and for feed ads, a copy with the platform's safe-zone overlay.
- **Landing-page loop:** muted, shorter and lighter, with a poster image. Its last frame should match its first.
- **Final inspection** on the encoded file: flickering thin lines, banding, rough edges, one-frame jumps, inconsistent scaling, clipped text, the loop seam.
