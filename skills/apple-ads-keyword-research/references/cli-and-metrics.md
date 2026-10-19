# CLI and metrics

Run from the installed skill directory, or replace the script path with its absolute location. The examples use environment credentials; add `--config /external/path/apple-ads.toml` to use a file. IDs are illustrative.

## Find accounts, apps, and campaigns

```sh
uv run scripts/apple_ads.py doctor
uv run scripts/apple_ads.py doctor --ad-account-id 123456789
uv run scripts/apple_ads.py apps --ad-account-id 123456789 --owned
uv run scripts/apple_ads.py apps --ad-account-id 123456789 --query "time tracking" --storefront DE
uv run scripts/apple_ads.py app --ad-account-id 123456789 --adam-id 1234567890
uv run scripts/apple_ads.py campaigns --ad-account-id 123456789 --adam-id 1234567890 --status ENABLED
```

- `doctor` without an account lists ad account IDs, names, and roles. With `--ad-account-id` it also returns the account's currency, time zone, status, and product features.
- `apps --query` searches app and developer names across the public App Store (at least 3 characters). `--owned` limits results to your organization's apps. `--storefront` repeats for several countries.
- `app` returns the primary and secondary genre as display names such as `Productivity`. Map them yourself to a `popularity` genre such as `PRODUCTIVITY_UTILITIES`.
- `campaigns` returns non-deleted campaigns with `countries`, `supply_placements`, `bid_strategy`, `daily_budget`, `display_status`, and Apple's status reasons.

## Performance reports

```sh
uv run scripts/apple_ads.py report --ad-account-id 123456789 --level campaigns --start 2026-09-01 --end 2026-09-30 --output campaigns.json
uv run scripts/apple_ads.py report --ad-account-id 123456789 --level keywords --campaign-id 444555666 --start 2026-09-01 --end 2026-09-30 --include-empty --output keywords.json --csv keywords.csv
uv run scripts/apple_ads.py report --ad-account-id 123456789 --level searchterms --campaign-id 444555666 --start 2026-09-01 --end 2026-09-30 --sort localSpend:desc --output searchterms.json
uv run scripts/apple_ads.py report --ad-account-id 123456789 --level keywords --campaign-id 444555666 --start 2026-07-01 --end 2026-09-30 --granularity weekly --group-by countryOrRegion --output weekly.json --csv weekly.csv
```

| Rule | Detail |
| --- | --- |
| Campaign scope | `adgroups`, `keywords`, and `searchterms` need exactly one `--campaign-id`; `--ad-group-id` narrows them. `campaigns` takes any number of IDs, or none for all. |
| Dates | `--start` and `--end` are inclusive. Omit `--granularity` for period totals. `hourly` covers at most 7 days starting within the last 365 days; `daily` at most 90 days; `weekly` at least 14; `monthly` at least 90. |
| Time zone | `ortz` (the account time zone, default) or `utc`. Search term reports accept only `ortz` and have no hourly data. |
| `--group-by` | Campaigns and ad groups: `deviceClass`, `ageRange`, `gender`, `countryCode`, `adminArea`, `locality`, `countryOrRegion`. Keywords and search terms: `deviceClass`, `countryOrRegion`. Each value adds a row per dimension value. |
| `--include-empty` | Adds entities without activity, such as keywords with no impressions. It cannot be combined with `--group-by`. |
| `--sort` | Apple's camelCase field and a direction, such as `localSpend:desc` or `taps:desc`. Repeat for tie-breakers. The API default is ID order. |

The CLI rejects these combinations before calling Apple; Apple enforces them too. [Report reference](https://developer.apple.com/documentation/apple-ads-platform-api/reports)

Report JSON contains `command`, `retrieved_at`, `api_version`, `ad_account_id`, `account`, `request`, `results`, `grand_total`, `currency`, `truncated`, `total_available`, and `warnings`. `grand_total` holds Apple's totals across every matching row, including rows beyond `--limit`. `currency` is the currency of the returned money; a warning appears if it differs from the account currency or varies between rows.

Each row starts with entity fields for its level, then any `--group-by` dimensions as snake_case (`country_or_region`, `device_class`, and so on), then the metrics below, then `granular`.

| Level | Entity fields |
| --- | --- |
| `campaigns` | `campaign_id`, `campaign_name`, `adam_id`, `status`, `display_status`, `ad_channel_type`, `bid_strategy`, `daily_budget`, `deleted` |
| `adgroups` | `ad_group_id`, `ad_group_name`, `campaign_id`, `status`, `display_status`, `pricing_model`, `bid_strategy`, `automated_keywords_opt_in`, `deleted` |
| `keywords` | `keyword_id`, `keyword`, `match_type` (`EXACT` or `BROAD`), `status`, `display_status`, `bid`, `campaign_id`, `ad_group_id`, `ad_group_name`, `deleted`, `bid_recommendation` |
| `searchterms` | `search_term`, `search_term_source` (`TARGETED` or `AUTO`), `keyword_id`, `keyword`, `match_type`, `campaign_id`, `ad_group_id`, `ad_group_name` |

| Metric | Meaning |
| --- | --- |
| `impressions`, `taps`, `ttr` | Ad impressions, taps, and taps per impression. |
| `local_spend`, `cpt`, `cpm` | Spend, average cost per tap, and average cost per thousand impressions, as decimal strings in `currency`. |
| `tap_installs`, `tap_install_rate`, `tap_install_cpi` | Installs after a tap, installs per tap, and spend per tap-through install. Use these to compare keywords and search terms. |
| `view_installs` | Installs Apple credits to an impression without a tap. |
| `total_installs`, `total_install_rate`, `total_avg_cpi` | Tap-through plus view-through installs, per tap, and spend per install. |
| `*_new_downloads`, `*_redownloads` | First-time downloads and redownloads, each with `tap_`, `view_`, and `total_` prefixes. |
| `tap_pre_orders_placed`, `view_pre_orders_placed`, `total_pre_orders_placed` | Pre-orders by attribution type. |
| `bid`, `daily_budget` | Configured amounts at report time, as decimal strings. |
| `bid_recommendation` | Apple's suggested keyword bid as a decimal string, or null. |
| `granular` | One entry per period with `date` (`YYYY-MM-DD`, or `YYYY-MM-DD HH` for hourly) and the same metrics. Empty without `--granularity`. |

Missing metrics stay `null`; observed zero stays zero. Search term rows without text get a warning; treat them as unattributed searches. The API caps a report page at 5,000 rows; the CLI pages through up to `--limit` (default 1,000).

## Keyword research

```sh
uv run scripts/apple_ads.py ideas --ad-account-id 123456789 --adam-id 1234567890 --country DE --term Zeiterfassung --output ideas-de.json
uv run scripts/apple_ads.py phrases --ad-account-id 123456789 --adam-id 1234567890 --output phrases.json
uv run scripts/apple_ads.py phrases --ad-account-id 123456789 --terms-file phrases.txt --output phrase-lookup.json
uv run scripts/apple_ads.py popularity --ad-account-id 123456789 --country DE --genre PRODUCTIVITY_UTILITIES --granularity monthly --start 2026-07-01 --end 2026-09-30 --output popularity-de.json --csv popularity-de.csv
uv run scripts/apple_ads.py popularity --ad-account-id 123456789 --country DE --granularity weekly --start 2026-09-06 --end 2026-10-10 --terms-file candidates.txt --output candidates-de.json
uv run scripts/apple_ads.py impression-share --ad-account-id 123456789 --adam-id 1234567890 --country DE --granularity daily --start 2026-09-19 --end 2026-10-18 --slot all --output share-de.json
```

`--term` repeats; `--terms-file` is UTF-8 with one term per line. Blank lines and exact duplicates are removed, and spelling is preserved.

| Command | Scope and limits |
| --- | --- |
| `ideas` | Apple's keyword suggestions for the promoted app, sorted by popularity. `--term` seeds them and `--country` limits them. One popularity score covers all requested countries, so the output warns unless exactly one country is given. |
| `phrases` | Exactly one route. `--adam-id` discovers phrases for the app. `--term`/`--terms-file` looks up popularity for exact phrases and returns `unmatched_terms`. `--like` matches part of a phrase. Apple's phrase endpoint takes no country filter. |
| `popularity` | Top search terms per country and genre. `--country` is required; `--genre` is optional and repeatable (omit it for all genres). Weekly data uses Sunday-to-Saturday weeks, is published each Monday, and is kept for 65 weeks. Monthly data uses calendar months, is published on the 5th for the previous month, and is kept for 15 months. Apple includes terms with at least 500 searches and 10 impressions, up to 500 per country and genre, in about 90 storefronts (not Russia or Belarus). `--term` filters to exact terms and returns `unmatched_terms`; `--contains` matches part of a term. |
| `impression-share` | Your app's share of ad impressions per search term. `--adam-id` is required and repeatable. `--slot first` (default) measures the top ad position only; `--slot all` any position. Daily data covers at most 30 days; weekly data starts on a Sunday and covers at most 4 weeks. Terms with fewer than 10 impressions are suppressed. |

Popularity and impression share always use UTC and accept at most two `--sort` fields. Suggestions page at 1,000 rows and insights at 5,000. [Insights reference](https://developer.apple.com/documentation/apple-ads-platform-api/insights-endpoints) · [Suggestions reference](https://developer.apple.com/documentation/apple-ads-platform-api/suggestions-endpoints)

| Row field | Meaning |
| --- | --- |
| `keyword`, `phrase`, `popularity` | Suggestion text and Apple's relative popularity (0–100). A score, not search volume. |
| `period` | Popularity: `YYYY-MM` for monthly; for weekly, Apple documents the Sunday after the completed week. Impression share: the day, or the Sunday that starts the week. Check returned periods against the request. |
| `country_or_region`, `genre`, `search_term` | The market, App Store genre, and search term the row describes. |
| `rank_in_genre` | Rank by search volume within the country and genre; 1 is the most searched. |
| `search_popularity_in_genre` | Popularity within the country and genre, 1–100. |
| `search_popularity_1to100`, `search_popularity_1to5` | Popularity across all genres in the country. The 1–5 scale matches the Search Popularity column in the Apple Ads UI. |
| `low_impression_share`, `high_impression_share` | Equal values give the share to one percent between 0.01 and 0.90. `0.91` and `1.0` together mean above 90%. |
| `rank` | Your app's impression share rank for the term and country; 1 is the highest share. |
| `adam_id`, `app_name` | The promoted app in impression share rows. |

`unmatched_terms` lists requested terms with no returned row, compared case-insensitively. It does not mean zero demand. When results are truncated it may also include terms beyond `--limit`, and a warning says so.

## Output contract

JSON goes to stdout unless `--output` names a file. With `--output`, stdout instead shows a compact tab-separated summary: a `key=value` header (command, ad account, currency, level or route, countries, dates, time zone, granularity, row count, `truncated`, `total_available`, unmatched count, output paths), a column header, then one line per row. Prefer `--output` for larger pulls and read specific fields from the file. `--csv` writes a second export.

Every JSON export has `command`, `retrieved_at` (UTC), `api_version`, `request`, `results`, and, for lists, `truncated` and `total_available`. `--limit` caps rows; the CLI requests one extra row to set `truncated`. `total_available` is Apple's count when it reports one and null otherwise.

CSV flattens each row, joins lists with semicolons, and adds `retrieved_at` and `currency`. A report with `--granularity` becomes long format, one line per entity and period, ready for a pivot table. Null cells are blank. Text cells that could start a spreadsheet formula (`=`, `+`, `-`, `@`, or a leading tab or carriage return) get an apostrophe prefix; JSON keeps the original text and is the authoritative export.

Diagnostics go to stderr. Malformed arguments exit 2; rejected combinations and runtime failures exit 1. A failed API call emits no dataset, even if earlier pages succeeded. Each file is replaced atomically, but JSON and CSV are written separately, so use the exit status to judge success. Output directories must already exist.

Requests time out after 30 seconds. The CLI retries rate limits, server errors, and network failures up to four attempts in total, waits as long as `Retry-After` says (at most 60 seconds), pauses when `RateLimit-Remaining` drops below 5, and never follows redirects. Run one process per ad account. [Rate limits](https://developer.apple.com/documentation/apple-ads-platform-api/rate-limits)
