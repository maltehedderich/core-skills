# Provider Links And Icons

Use this table as defaults, then verify provider URL behavior if exact deep-link support matters. Most providers use a `q` query parameter; Grok uses `text`.

| Provider label | Default URL builder | Simple Icons icon |
| --- | --- | --- |
| Google AI | `https://www.google.com/search?udm=50&aep=11&q=${encodedPrompt}` | Prefer `simple-icons:googlegemini`; use `simple-icons:googleassistant` only when the target design expects the Assistant-style multicolor mark. |
| Claude | `https://claude.ai/new?q=${encodedPrompt}` | `simple-icons:claude` |
| ChatGPT | `https://chatgpt.com/?q=${encodedPrompt}` | `simple-icons:openai` because Simple Icons exposes OpenAI rather than a distinct ChatGPT icon in common Iconify sets. |
| Grok | `https://x.com/i/grok?text=${encodedPrompt}` | `simple-icons:x` as the Simple Icons-compatible fallback for the X-hosted Grok entry point. If the user requires the Grok logo specifically, ask before using a non-Simple-Icons asset. |
| Perplexity | `https://www.perplexity.ai/?q=${encodedPrompt}` | `simple-icons:perplexity` |

## Implementation Notes

- Keep provider IDs stable and framework-friendly: `google-ai`, `claude`, `chatgpt`, `grok`, `perplexity`.
- Encode exactly the final prompt string with `encodeURIComponent`.
- Prefer the current canonical domain over a route-local URL for site-wide footers.
- If the target site is not a company page, adapt the prompt noun and heading:
  - Portfolio: `Ask AI about {PERSON}`
  - Product site: `Ask AI about {PRODUCT}`
  - Documentation site: `Ask AI about this project`
  - Content site: `Ask AI about this website`
- Do not include UTM parameters or tracking fragments inside the prompt URL unless the site already treats those as canonical.

## Minimal Data Shape

```ts
const prompt =
  `Please provide a concise summary of this ${entityType}: ${canonicalUrl}. ` +
  'Include the main points, key insights, and conclusions.';

const encodedPrompt = encodeURIComponent(prompt);

const aiSummaryProviders = [
  {
    id: 'google-ai',
    label: 'Google AI',
    icon: 'simple-icons:googlegemini',
    href: `https://www.google.com/search?udm=50&aep=11&q=${encodedPrompt}`,
  },
  {
    id: 'claude',
    label: 'Claude',
    icon: 'simple-icons:claude',
    href: `https://claude.ai/new?q=${encodedPrompt}`,
  },
  {
    id: 'chatgpt',
    label: 'ChatGPT',
    icon: 'simple-icons:openai',
    href: `https://chatgpt.com/?q=${encodedPrompt}`,
  },
  {
    id: 'grok',
    label: 'Grok',
    icon: 'simple-icons:x',
    href: `https://x.com/i/grok?text=${encodedPrompt}`,
  },
  {
    id: 'perplexity',
    label: 'Perplexity',
    icon: 'simple-icons:perplexity',
    href: `https://www.perplexity.ai/?q=${encodedPrompt}`,
  },
];
```
