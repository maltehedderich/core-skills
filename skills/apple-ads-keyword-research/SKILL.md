---
name: apple-ads-keyword-research
description: Read Apple Ads (formerly Apple Search Ads) campaign data and research App Store keywords through the Apple Ads Platform API. Use for campaign, ad group, keyword, or search term performance (spend, taps, installs, CPT, CPI), Apple's keyword and phrase suggestions, relative App Store search popularity by country and genre, impression share and rank, ASO keyword ideas, or deciding which App Store keywords to add, pause, negate, or bid on. Read-only; it never changes campaigns.
---

# Apple Ads Keyword Research

Use observed Apple Ads data to make keyword and campaign decisions. The script retrieves data; the agent judges intent, relevance, evidence, and priority.

## Choose the decision

- **Campaign performance:** how campaigns, ad groups, keywords, or search terms perform, where spend produces no installs, and which search terms to add as exact keywords or negatives. Use `campaigns` and `report`.
- **Keyword research for ads or ASO:** what people search for in the App Store and how popular it is. Use `ideas`, `phrases`, and `popularity`; add `impression-share` when the app already runs ads. None of these need spend history.
- **Both:** keep observed performance separate from popularity-based discovery. A popular term with no performance data is a candidate to test.

Research never authorizes changes. Present keyword additions, negatives, pauses, and bid changes as proposals for the user to apply.

## Establish the brief

Identify the app (its Adam ID; `apps --owned` lists them), the App Store countries or regions, the date range, and the goal: installs at a target CPI or CPT, brand defense, or discovery. Ask when the country is missing. Do not default to the US or the account's home market. Apple Ads targets storefronts, not languages, so note when a storefront has customers searching in more than one language.

Keep markets separate. Suggestion popularity blends every requested country, so request one country per call to rank a market. Popularity and impression share rows are per country; never sum or average them into a combined market.

## Get access and choose a command

Run the bundled script by its installed absolute path:

```sh
uv run /path/to/apple-ads-keyword-research/scripts/apple_ads.py --help
```

Read [setup.md](references/setup.md) for first-time API access, missing credentials, or access errors. Credentials come from an external TOML file via `--config` or from `APPLE_ADS_*` environment variables. Never ask the user to paste a private key, client secret, or token into chat. Start with `doctor` to list the ad accounts the credentials can reach, then run `doctor --ad-account-id ID` to verify one.

Read [cli-and-metrics.md](references/cli-and-metrics.md) for arguments, output fields, limits, and interpretation.

- `apps` and `app` find the Adam ID, its storefronts, and its primary genre.
- `campaigns` lists campaigns with status, countries, budget, and bid strategy. Use it to find campaign IDs.
- `report --level campaigns|adgroups|keywords|searchterms` returns performance for a date range. Ad group, keyword, and search term reports take exactly one `--campaign-id`, so loop over campaigns for an account-wide view. `--include-empty` adds keywords that had no activity. `--granularity` adds a time series; omit it for period totals.
- `ideas` returns Apple's keyword suggestions for a promoted app, optionally seeded with `--term` and limited by `--country`.
- `phrases` discovers search phrases for an app (`--adam-id`), looks up the popularity of known phrases (`--term`), or matches part of a phrase (`--like`).
- `popularity` returns the top search terms for a country and App Store genre with rank and popularity scores, weekly or monthly. Use `--term` to check specific candidates.
- `impression-share` shows how often the app's ads appeared for each search term, its rank against other advertisers, and the term's 1–5 popularity.
- For more than a handful of rows, pass `--output file.json` (and `--csv` if wanted). Stdout then shows a compact TSV summary instead of the full JSON; read the file only for the fields you need.

Every command reads data. The client sends only GET requests and POST requests to `/query` endpoints, and refuses anything else.

Do the setup and research work you can, then name the exact missing user action if API access blocks live calls. Missing access never justifies invented popularity, spend, or install numbers.

## Select and explain

1. Apply product relevance first: what does the searcher want, and can this app give it to them? Hold ambiguous terms. Treat competitor brand names as a separate conquesting decision for the user.
2. Compare keywords and search terms on tap-through metrics (`tap_installs`, `tap_install_rate`, `tap_install_cpi`). The `total_*` metrics add view-through installs that Apple credits to impressions. Say which basis you use, and say when a keyword has too few taps to judge.
3. Search term reports show what people typed. A search term with good tap-through installs that is not yet an exact keyword is a candidate to add as one; an irrelevant or expensive term without installs is a negative candidate. `search_term_source: AUTO` means Apple matched the search automatically. Rows without search term text are unattributed searches.
4. Popularity is relative. `popularity` (suggestions, 0–100), `search_popularity_1to100`, `search_popularity_1to5`, and `rank_in_genre` are scores and ranks. Never convert them into monthly searches or compare them with Google volumes. A term missing from `popularity` fell below Apple's threshold or outside the top 500 for that country and genre; its demand is unknown.
5. Impression share shows headroom. Low share on a popular, converting term points to bid, budget, or relevance limits. A share of 0.91–1.0 means above 90%, where a higher bid buys little. `bid_recommendation` is Apple's suggestion and says nothing about affordability. When the user gives a target CPI, the break-even CPT is that CPI times the observed `tap_install_rate`; label it an estimate and show both inputs.
6. Preserve null versus zero, the date range, the time zone, currency, country, and truncation. Reports default to the account time zone (`ORTZ`), search term reports only support it, and popularity and impression share always use UTC. A truncated response is a sample, ordered by the requested sort rather than by priority.

## Deliver

Give a short answer backed by the data. For performance, rank keywords or search terms with spend, taps, installs, CPI, and the period. For research, group a shortlist by intent with popularity, rank, country, and the reason for each pick. Separate observations from proposals (add, pause, negate, change a bid), and include exclusions or uncertainties that change the decision.

Link requested JSON and CSV exports and state the ad account, app, countries, period, time zone, currency, retrieval time, and any truncation or missing data. Keep raw exports separate from your judgment. Reuse exports for follow-up questions when their scope and freshness fit: monthly popularity updates on the 5th of each month, weekly popularity every Monday.
