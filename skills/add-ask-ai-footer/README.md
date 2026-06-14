# Ask AI Footer

Ask AI Footer helps an assistant add a compact "Ask AI about ..." section to a website or web app footer.

Use it when you want footer links that open AI assistants with a prefilled prompt asking for a concise summary of the company, product, person, project, or website.

## Install the Skill

From the repository root:

```sh
./coreskills install --tool codex --skills add-ask-ai-footer
```

Replace `codex` with `claude`, `copilot`, or `gemini` when you use a different tool.

## Add the Footer Section

Ask your assistant to use the skill against a frontend repository or local app:

```text
Use $add-ask-ai-footer to add an Ask AI footer section to this website.
```

If the production URL is not obvious from the repository, include it:

```text
Use $add-ask-ai-footer to add an Ask AI footer section for https://example.com.
```

## What the Skill Adds

The skill implements real links for common AI assistants:

| Provider | Link behavior |
| --- | --- |
| Google AI | Opens Google AI Mode search with the encoded prompt. |
| Claude | Opens Claude with the encoded prompt. |
| ChatGPT | Opens ChatGPT with the encoded prompt. |
| Grok | Opens the X-hosted Grok entry point with the encoded prompt. |
| Perplexity | Opens Perplexity with the encoded prompt. |

The detailed provider URL and icon defaults live in [`references/providers.md`](references/providers.md).

## Implementation Expectations

The assistant should reuse the target app's footer, routing, styling system, icon pipeline, and package manager. It should derive the production canonical URL from the project when possible, use accessible external links, source provider icons through Simple Icons when viable, and match the existing footer design.

Before finishing, it should run the relevant formatter, typecheck, tests, and build, then inspect desktop and mobile footer layouts.
