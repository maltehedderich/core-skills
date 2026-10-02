# CLI and metrics

Run from the installed skill directory, or replace the script path with its absolute location. All examples use environment credentials; add `--config /external/path/google-ads.yaml` to use YAML instead.

## Resolve a market

```sh
uv run scripts/google_keywords.py locations --customer-id 1234567890 --name Germany --country-code DE
uv run scripts/google_keywords.py languages --customer-id 1234567890
```

Location results include canonical name, country, target type, and status. Choose an enabled intended location; ask about ambiguity. Languages include the Google ID, language code, name, and targetability. These lookup results are not proof of planning access.

## Research

The examples below explicitly target Germany (`2276`) and German (`1001`):

```sh
uv run scripts/google_keywords.py ideas --customer-id 1234567890 --keyword Zeiterfassung --geo-id 2276 --language-id 1001 --limit 200 --output ideas.json --csv ideas.csv
uv run scripts/google_keywords.py ideas --customer-id 1234567890 --url https://example.com/product --keyword Zeiterfassung --geo-id 2276 --language-id 1001
uv run scripts/google_keywords.py ideas --customer-id 1234567890 --site example.com --geo-id 2276 --language-id 1001 --output site-ideas.json
uv run scripts/google_keywords.py metrics --customer-id 1234567890 --keywords-file keywords.txt --geo-id 2276 --language-id 1001 --output metrics.json --csv metrics.csv
uv run scripts/google_keywords.py metrics --customer-id 1234567890 --keywords-file keywords.txt --geo-id 2276 --language-id 1001 --from-month 2024-10 --to-month 2025-03 --output winter.json
```

- Repeat `--keyword` to supply phrases. `--keywords-file` is UTF-8, one phrase per line; blank lines and exact duplicate inputs are removed. Do not supply a CSV as this input.
- `ideas` requires keywords, an HTTP(S) URL, or both, or `--site`. At most 20 seed keywords are accepted. URL seeding uses a page, not an entire-site crawl. `--site example.com` seeds from a whole domain (bare hostname: no scheme, path, port, or credentials; internationalized names are converted to punycode) and cannot be combined with keywords or `--url`.
- `--geo-id` accepts up to 10 Google geo-target IDs. Multiple locations are combined in one market. `--worldwide` explicitly replaces geo IDs. Language is always required for research.
- `--network google` is the default. Choose `google-and-partners` explicitly to include search partners.
- `--limit` caps ideas at 200 by default; results use API order. Pagination stops at the limit and `truncated` indicates whether more were available; `total_available` is Google's reported total idea count (null when not reported). An empty response is successful and has no rows.
- Historical lists are batched at 10,000 keywords. Google may consolidate close variants within each batch. Rows from separate batches can overlap; do not add them together. [Historical request definition](https://developers.google.com/google-ads/api/reference/rpc/v25/GenerateKeywordHistoricalMetricsRequest)
- Statistics use the API's default historical window, approximately the previous 12 months. `--from-month YYYY-MM --to-month YYYY-MM` (ideas, metrics, and `doctor --check-planning`) requests a custom inclusive window instead: give both, in order, ending before the current month. Google limits how far back data is available and returns an error for unsupported ranges. `request.period` records the window used; inspect `returned_months` for actual coverage. Forecasts use the separate command below.
- Existing output files are replaced when their paths are explicitly supplied; output directories must already exist. JSON and CSV paths must differ and cannot match input configuration or keyword files.

## Output contract

JSON is written to stdout unless `--output` names a file. With `--output`, stdout instead gets a compact tab-separated summary: a `key=value` header (command, market, language, network/period or forecast dates, row count, `truncated`, `total_available`, unmatched count, output paths), a column header, then one line per row. Research rows show keyword, average monthly searches, competition, low/high top-of-page bid, average CPC, and brand concepts (`TYPE:name`); forecasts show clicks, cost, average CPC, and daily values; lookups show their IDs and names. Prefer `--output` for larger pulls and read specific fields from the file. `--csv` optionally writes a second export. Diagnostics go to stderr; invalid arguments exit 2 and runtime failures exit 1. A runtime API failure emits no successful dataset, even if earlier batches succeeded. Results are collected before file writes, and individual files are replaced atomically. JSON and CSV are not a filesystem transaction: if a later write fails, an earlier file may exist; use the exit status to determine success.

Research JSON contains:

- `command`, `retrieved_at` (UTC), `api_version`.
- `account`: customer ID, account currency, test-account status.
- `request`: keywords/URL/site, geo IDs or worldwide, language, network, period, and ideas limit where relevant.
- `results`: the keyword rows described below.
- `returned_months`, `truncated`, `warnings`; ideas also have `total_available`; historical results also have `unmatched_keywords`.

| Row field | Meaning |
| --- | --- |
| `keyword` | Google's returned keyword text; may differ from the input. |
| `close_variants` | Google's historical grouping, when returned. Ideas generally have none. |
| `avg_monthly_searches` | Approximate monthly demand over the reported period. |
| `monthly_search_volumes` | Chronological `{month: YYYY-MM, searches: number or null}` entries. |
| `competition` / `competition_index` | Advertiser competition category and index (0–100), not SEO difficulty. |
| `low_top_of_page_bid_micros` / `high_top_of_page_bid_micros` | Historical 20th/80th percentile bid estimates in millionths of account currency. |
| `low_top_of_page_bid` / `high_top_of_page_bid` | Decimal strings converted to account currency, without floating-point rounding. |
| `average_cpc_micros` / `average_cpc` | Historical average CPC advertisers paid, in micros and decimal account currency. Auction context, not a predicted CPC for a new campaign. |
| `concepts` | Ideas only: Google's keyword concepts as `{name, group, group_type}`; `group_type` is `BRAND`, `OTHER_BRANDS`, `NON_BRAND`, or null. A brand group is a hint for judging brand intent, not a classification. Historical rows have no `concepts` key. |

Missing optional fields remain `null`; observed zero stays zero. `unmatched_keywords` means no returned text or close variant matched that input (case-insensitively); it does not establish zero demand. Google's grouped demand must not be represented as an independent observation for every spelling. [Google's historical metrics guide](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-historical-metrics)

CSV flattens each row and adds currency, market settings, retrieval time, truncation, and a column per returned month. Null cells are blank. Close variants, geo IDs, and concepts (`TYPE:name`) use semicolon-separated cells. Text cells that could start a spreadsheet formula (`=`, `+`, `-`, `@`, or a leading tab/carriage return) are prefixed with an apostrophe; JSON preserves original text. JSON is the authoritative export, including unmatched inputs and warnings.

Calls have a 30-second RPC timeout and at most three attempts for transient errors or throttling. Planning calls are paced at least 1.05 seconds apart within one process. Run one process per customer to respect the shared quota. Reuse suitable exports: Google says historical metrics refresh monthly. [Planning overview](https://developers.google.com/google-ads/api/docs/keyword-planning/overview) · [Quotas](https://developers.google.com/google-ads/api/docs/best-practices/quotas)

## Read-only forecasts

Use after selecting survivors and computing a CPC ceiling. This calls `KeywordPlanIdeaService.GenerateKeywordForecastMetrics`; it creates neither campaigns nor saved plans. The existing `ideas` / `metrics` output contracts are unchanged.

```sh
uv run scripts/google_keywords.py forecast --customer-id 1234567890 --plan-file forecast-plan.json --output forecast.json --csv forecast.csv
```

In viability mode, generate this file with `search_viability.py evaluate --forecast-plans DIR` rather than writing it by hand; the calculator checks forecasts against the same plan. Example scenario (illustrative money and dates; replace with the real future test window):

```json
{
  "currency_code": "EUR",
  "geo_ids": ["2276"],
  "language_id": "1001",
  "start_date": "2027-01-01",
  "end_date": "2027-01-14",
  "daily_budget": "5",
  "max_cpc": "0.720000",
  "bidding_strategy": "manual_cpc",
  "ad_groups": [{
    "id": "buyers",
    "keywords": [{"text": "scheduling software", "match_type": "EXACT"}]
  }]
}
```

- Currency must match the account; no implicit conversion. Monetary values are positive account-currency amounts with at most six decimal places. In viability mode, use the calculator's `forecast_max_cpc` (rounded down).
- Supply explicit unique `geo_ids` (up to 10), or omit them and set `worldwide: true`. Language is required. Groups need unique IDs and at least one keyword with `EXACT` or `PHRASE` match type.
- Dates are inclusive ISO dates. Start must be in the future; end must be within one calendar year from today, evaluated in the Google Ads account timezone. The command reads that timezone before requesting a forecast. It never accepts the API's implicit default week.
- `manual_cpc` sends daily budget and maximum CPC. `maximize_clicks` sends daily target spend and a CPC ceiling. Account-specific minimum budgets can still cause a Google API error; do not automatically increase the user's budget to resolve it.
- v25 does **not** accept negatives, network selection, or per-ad-group bids in this request. Unknown plan fields are rejected instead of silently dropped. Keep proposed network settings and negatives in the launch brief and disclose the unmodeled settings.
- Forecasts are campaign totals for the supplied period, not daily totals. They return no ad-group allocation. Separate profile scenarios cannot be added into a combined campaign forecast.

Forecast JSON contains `command`, `retrieved_at`, `api_version`, `account`, `account_timezone`, the full scenario under `request`, `period_days`, `metrics_basis: period_total`, and `warnings`. Its `results` is an object containing:

| Field | Meaning |
| --- | --- |
| `clicks` | Estimated total clicks over the inclusive forecast period. |
| `cost_micros` / `cost` | Total estimated cost in micros and decimal account currency. |
| `average_cpc_micros` / `average_cpc` | Estimated average CPC; unavailable when no clicks are forecast. |
| `daily_clicks` / `daily_cost` | Derived period totals divided by `period_days`, as decimal strings. |

Missing values remain null and zeros remain zero. No conversions are requested or used; calculate them from the explicit funnel assumptions. CSV is one campaign row containing those fields, dates, currency, retrieval time, and limitations. Forecast request/response behavior uses the existing retries, pacing, and error handling. Input plan and configuration files cannot be overwritten by exports.

The pinned v25 protobuf/SDK contract is authoritative when an older guide or code sample differs: [request definitions](https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/services/keyword_plan_idea_service.proto). For economics and go/no-go decisions, use [the viability loop](search-viability-loop.md) and [offline calculator](viability-calculator.md).
