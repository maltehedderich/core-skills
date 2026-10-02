# Offline viability calculator

Run with `uv`; the script declares Python 3.11+ and uses only the standard library; no credentials or API calls. Paths below are relative to the installed skill directory. Resolve evidence paths relative to the input JSON, not the current shell directory.

```sh
uv run scripts/search_viability.py economics --input brief.json --output economics.json --csv economics.csv
uv run scripts/search_viability.py scaffold --historical metrics.json --profile-id buyers --input plan.json --output buyers-keywords.json
uv run scripts/search_viability.py evaluate --input plan.json --output decision.json --forecast-plans plans/
uv run scripts/search_viability.py evaluate --input plan.json --output decision.json --csv decision.csv --keywords-csv keywords.csv --negatives-csv negatives.csv
```

`scaffold` reads an `ideas` or `metrics` export and emits `{"id", "historical_file", "keywords": [...]}`. Each entry has `keyword`, `match_type: "PHRASE"`, `commercial_intent: null`, and `brand: true` when Google returned a `BRAND`/`OTHER_BRANDS` concept (otherwise null), plus read-only context (`avg_monthly_searches`, `high_top_of_page_bid`, `average_cpc`, `concepts`). Paste it into the profile, set every `commercial_intent` and `brand`, switch the strongest terms to EXACT, and delete irrelevant entries; `evaluate` ignores the context fields. With `--input`, the export's currency and market must match the brief and `historical_file` is relative to the brief.

`evaluate --forecast-plans DIR` writes `<profile_id>.forecast-plan.json` per profile and `campaign.forecast-plan.json` for the selected profiles, in the exact `forecast --plan-file` format, into an existing directory. A plan is skipped with a reason (no kept keywords, test dates, daily budget, positive CPC ceiling, complete market, or campaign selection). The result JSON lists `forecast_plans` as `{id, path, skipped}`. Profile IDs must be file-name safe (letters, digits, `.`, `_`, `-`) to write plans. The forecast gate compares exports against the same plan, so regenerate plans whenever survivors or settings change.

Both commands retain input and assumption provenance. `economics` returning READY allows keyword research; it is not a viability GO. `evaluate` reports profile and campaign GO / NO_GO / INCOMPLETE. Decision outcomes exit 0, including NO_GO; malformed input, unreadable referenced files, or incompatible historical settings exit 1. An omitted evidence path means unknown; a supplied but invalid path is an input error.

JSON is authoritative and goes to stdout unless `--output` names a file. With `--output`, stdout gets a compact tab-separated summary instead: a header with the command and output paths, then one line per profile and the campaign (`id`, `status`, `max_cpc`, failed gates, unknown gates) and one `forecast_plan` line per written or skipped plan; `scaffold` prints only its header with keyword and brand-hint counts. Decimal money and calculated values serialize as strings; null remains unknown. CSV has one profile/campaign per row, a column per gate, and readable failed/unknown gate lists and required actions. Keyword and negative exports are separate CSVs, with spreadsheet-formula protection. Output paths must differ and cannot overwrite input or evidence files. Files are individually atomic, not a multi-file transaction. A failed command can leave an earlier output file; check its exit status.

## Input

This illustrative plan uses invented numbers and unverified readiness. Replace dates with an explicit future 14-day interval, replace evidence paths with real exports, and replace assumptions with offer-specific inputs. Do not present this example as observed data.

For `economics`, only offer, market, profile id/economics, and optional sources are needed. For `evaluate`, add the remaining fields. Omit unavailable exports while collecting evidence; do not fabricate files to complete the example.

```json
{
  "offer": {
    "name": "Scheduling software",
    "price": "100",
    "billing_basis": "first monthly payment",
    "conversion_action": "purchase",
    "conversion_type": "purchase",
    "landing_page_url": "https://example.com/buy",
    "landing_page_live": {"verified": null, "evidence": null}
  },
  "market": {
    "currency_code": "EUR",
    "geo_ids": ["2276"],
    "language_id": "1001",
    "network": "google"
  },
  "test": {
    "start_date": "2027-01-01",
    "end_date": "2027-01-14",
    "daily_budget": "5",
    "total_budget": "70"
  },
  "profiles": [{
    "id": "buyers",
    "job": "Replace manual appointment booking this week",
    "why_pay": "Reduce paid administrative time",
    "search_stage": "ready_to_buy",
    "disqualifier": "Students looking for a class scheduling worksheet",
    "economics": {
      "billing_basis": "first monthly payment",
      "first_order_revenue": "100",
      "variable_costs": "20",
      "repeat_probability": "0",
      "page_type": "cold_saas"
    },
    "sources": {
      "first_order_revenue": {"source": "user_estimated", "evidence": "Illustrative first payment"},
      "variable_costs": {"source": "user_estimated", "evidence": "Illustrative fees and support"},
      "repeat_probability": {"source": "user_estimated", "evidence": "Assume no repeat for this scenario"}
    },
    "daily_budget": "5",
    "historical_file": "metrics.json",
    "forecast_file": "buyers-forecast.json",
    "keywords": [{
      "keyword": "scheduling software",
      "match_type": "EXACT",
      "commercial_intent": true,
      "brand": false
    }],
    "negatives": [{
      "keyword": "jobs",
      "match_type": "PHRASE",
      "scope": "campaign",
      "reason": "Exclude hiring intent"
    }],
    "negative_review": {"verified": null, "evidence": null},
    "readiness": {
      "landing_page_match": {"verified": null, "evidence": null},
      "tracking": {"verified": null, "evidence": null}
    }
  }],
  "campaign": {
    "profile_ids": ["buyers"],
    "forecast_file": "combined-forecast.json"
  }
}
```

### Fields and overrides

- Offer `conversion_type`: `purchase`, `lead`, `trial`, or `signup`; `conversion_action` identifies the actual single event. Readiness evidence must describe that event, page, and check date. `verified: true` without a nonempty evidence string remains unknown. The calculator records supplied evidence; it does not itself inspect pages or exercise tracking.
- Market: account currency, explicit geo IDs or `worldwide: true`, language ID, and historical network (default `google`). Optional `time_zone` (IANA, e.g. `Europe/Berlin`) makes the future-date check use the account's calendar day; copy `account_timezone` from a forecast export. Without it, the local date is used. Keep different markets in separate plans. Convert economic inputs into account currency explicitly before calculation; do not silently convert API data.
- Economics: `first_order_revenue`, `variable_costs`, matching `billing_basis`, `repeat_probability`, and `repeat_contribution` when probability is nonzero. Missing values remain unknown. Negative first-order contribution fails.
- Optional economics: `acquisition_share` (default 0.30), `close_rate` (default 0.20 for non-purchases), `landing_conversion_rate` (0.03 for `page_type: cold_saas`, 0.05 for `local_service`, otherwise required). Rates use fractions, not percentages. Purchases use close rate 1. All must be finite; rates must be in [0, 1].
- `sources` is keyed by economics input name; each value contains `source` and optional `evidence`. Use observed/user_estimated/default accurately. Omitted labels become supplied_unverified. Changed assumptions and their rationale belong here.
- Profiles: unique IDs, job, why_pay, disqualifier, search_stage, and allocated daily budget. Candidate stages are ready_to_buy / late_solution_aware. An ineligible stage fails; an omitted stage remains unknown.
- Keywords: text, EXACT/PHRASE match type, explicit commercial_intent and brand booleans. Optional `decision` is keep/park/exclude, with `reason`. A keep that overrides the affordability default requires `override_reason`. Brand/informational terms cannot be forced into this non-brand test.
- Each keyword output row reports `match_status` (`matched`, `unmatched`, `ambiguous`, `no_history`) and carries the matched row's `average_cpc` and `concepts` for reporting; neither affects a gate. A keep requires the high bid strictly below Max CPC. Missing or overlapping historical matches remain unpriced, and the default park reason names the match problem; close variants share an evidence group index. No summed demand field is produced. Low-volume flags do not automatically reject a cluster.
- Optional profile `stress_cpc` requires `stress_cpc_reason`; use for documented alternative evidence or sensitivity. Otherwise the highest surviving high bid is used, provided none is unknown.
- Optional `test.bidding_strategy`: `manual_cpc` (default for generated plans) or `maximize_clicks`. When set, forecast exports must use it; when omitted, either click strategy is accepted.
- Optional `test.thresholds`: `test_days` (14), `min_clicks` (100), `min_daily_clicks` (10), `low_volume` (30). Overrides must be positive integers and require `test.override_reason`. A different date-window length also needs this reason. Budgets must be nonnegative.
- Campaign selection is explicit. Each selected profile must pass individually and its allocation must fit the campaign's daily and total budget. No selection leaves the campaign INCOMPLETE; excluded failing profiles do not veto a passing selected subset.

### Forecast connection

Use the forecast command documented in [cli-and-metrics.md](cli-and-metrics.md) with the files from `evaluate --forecast-plans`. Each profile export must have exactly its surviving terms, match types, ID, allocated budget, market, dates, and `forecast_max_cpc` from economics. This cap rounds down to six decimal places so the API never receives a bid above the economics ceiling.

Use the combined export for all selected groups with the campaign daily budget and lowest selected CPC ceiling. For a single selected profile with identical budget and keywords, its export can serve both roles. The calculator verifies scenario equality; mismatches yield an unknown forecast gate whose reason lists the differing fields (for example `max_cpc, ad_groups`) and the plan file to rerun. Independent scenarios are never summed. Forecast scope is v25 period totals and does not model negatives or network selection.

The decision JSON includes both expected API clicks and budget-limited purchasable clicks. API cost remains in the evidence snapshot; stress spend is calculated separately. Campaign conversion and CPA calculations use a conservative envelope across profiles, not invented ad-group forecasts. Every gate retains a reason; the agent should turn failed/unknown gates into a concise explanation and specific next actions.
