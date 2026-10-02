---
name: google-keyword-research
description: Research Google keywords for SEO and paid search using Google Ads planning data (Keyword Planner). Use for keyword ideas, search volume, "how many people search for" questions, CPC and bid estimates, competition, seasonality, or a Search Viability Loop that prices commercial keyword clusters against contribution-based acquisition ceilings and read-only forecasts before proposing a paid test.
---

# Google Keyword Research

Use observed Keyword Planner data to make a relevant keyword selection. Scripts retrieve data and calculate scenarios; the agent judges intent, product fit, evidence, and priority.

## Choose the decision

- **SEO or raw research:** use the brief, research, and shortlist flow below. Do not require an offer, margins, conversion tracking, or a viability exercise for these requests.
- **Paid-search viability:** when the user asks whether Search ads can work, what they can afford, or to run the Search Viability Loop, read [search-viability-loop.md](references/search-viability-loop.md). Lock the offer and calculate acquisition ceilings before building keyword clusters. Use the offline calculator and read-only forecasts to produce a decision sheet.
- **Both:** maintain separate SEO and paid-search conclusions. Informational terms can be useful for SEO while failing the first paid test's intent filter.

A request for paid keyword ideas or bid data alone does not require the full viability mode. Do not infer campaign execution permission from research or a GO result.

## Establish the brief

Read supplied product context and keyword lists. Establish the audience, product or topic, and whether the decision concerns SEO, paid search, or both. Use the request's geography and language; ask when either is missing. Do not silently default to the US or the account's locale.

Keep separate markets in separate runs and rankings. Multiple geo IDs in one call describe a combined market, not individual country results. Worldwide targeting requires an explicit request. If only raw metrics are requested, return them without imposing a strategy exercise.

## Get access and choose a command

Run the bundled script using its installed absolute path:

```sh
uv run /path/to/google-keyword-research/scripts/google_keywords.py --help
```

Read [setup.md](references/setup.md) for first-time authentication, missing credentials, or access errors. Use external YAML via `--config` or Google Ads environment variables. Never ask the user to paste credentials into chat. `doctor` checks account access; only `doctor --check-planning` verifies planning access.

Read [cli-and-metrics.md](references/cli-and-metrics.md) for arguments, output fields, limits, and interpretation.

- Use `locations` and `languages` to resolve market IDs. Select the intended location from the returned canonical names; do not silently resolve ambiguous names.
- Use `ideas` for keyword discovery from seed terms, a URL, or both, or from a whole domain with `--site`. Use coherent themes and a relevant product or landing-page URL. Google receives the supplied terms, URL, or domain.
- Use `metrics` to measure an existing list. Ideas already contain historical metrics, so a second call is usually unnecessary. `--from-month/--to-month` selects a custom historical window, e.g. to compare seasons.
- For more than a handful of rows, pass `--output file.json` (and `--csv` if wanted). Stdout then shows a compact TSV summary instead of the full JSON; read the file only for the fields you need.
- Use `forecast` only after selecting a commercial cluster and establishing its budget and CPC ceiling. It models a proposed scenario without saving a plan or creating a campaign. Its v25 limitations are documented in the CLI reference.
- All commands read account data or generate planning results. They do not create campaigns, saved plans, bids, or budgets.

Do the accessible setup and research work, then identify the exact missing user action if OAuth consent or Cloud approval prevents live calls. Continue with clearly labeled provisional candidates if useful. Missing access never justifies fabricated volumes, bids, or competition scores.

## Select and explain

1. Apply product relevance first: identify what the searcher wants and whether the product or proposed content can satisfy it. Hold ambiguous terms and exclude unsupported promises.
2. Group the returned terms by intent or use case. Rank by relevance, intent, observed demand, seasonality, and business value. Explain the tradeoffs instead of hiding them behind an arbitrary composite score.
3. For SEO, use volume as demand evidence. Verify the live search results before claiming an intent match or an achievable ranking opportunity: use web search or browser tools when available, in the target market and language where possible, and note the result types (organic, local pack, shopping, video, AI overview), whether ads appear, and which page types rank (product, category, comparison, guide, forum). Without such a tool, label the intent assessment unverified. Google Ads competition measures advertising, not organic difficulty.
4. For paid research, use advertiser competition and bid ranges as auction context. They do not establish an affordable bid, conversion rate, or profitability. Route affordability and test-budget decisions to the viability loop, which keeps observations, forecasts, and assumptions separate.
5. Idea rows carry Google's keyword `concepts`. A `BRAND` or `OTHER_BRANDS` concept is a brand hint, not a verdict; you still judge brand and intent from the term and market.
6. Preserve null versus zero, returned close-variant groups, and each market's settings. Do not sum overlapping groups into a total addressable search market. Treat a truncated ideas response as a sample; its API order is not a priority ranking.

## Deliver

Provide a concise ranked shortlist with intent, relevance, available metrics, seasonal observations, and a reason for selection. Separate SEO and advertising implications when both are requested. Include exclusions or uncertainties that change the decision.

For viability work, `search_viability.py scaffold` turns a metrics/ideas export into profile keyword entries for you to judge, and `evaluate --forecast-plans DIR` writes the exact forecast plan files the gates check. Deliver the reference's decision CSV, input/result JSON, keyword and negative exports, and a concise GO / NO_GO / INCOMPLETE explanation. `economics` returning READY means only that the economics brief is ready for keyword research. Only `evaluate` can return a full viability decision, and the proposed campaign needs its own combined check.

Link requested JSON/CSV exports and state geography, language, network, retrieval time, returned months, and any truncation or missing data. Preserve raw API output separately from your judgment. Reuse task exports for follow-up analysis when their settings and freshness fit; historical statistics refresh monthly. An unavailable result is unknown demand, not zero demand.
