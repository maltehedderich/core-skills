# Search Viability Loop

Use for a paid-search affordability or first-test decision. Preserve ordinary SEO and raw keyword research as separate, lightweight tasks. This workflow ends with a proposed test, not a campaign mutation.

## Command flow

1. `search_viability.py economics` on the brief: CPC ceilings before any keyword work.
2. `google_keywords.py ideas` / `metrics` with `--output`, per market.
3. `search_viability.py scaffold --historical metrics.json --profile-id ID --input plan.json` turns the export into profile keyword entries.
4. Judge each entry: set `commercial_intent` and `brand`, adjust match types, drop irrelevant terms, add negatives.
5. `search_viability.py evaluate --forecast-plans DIR` writes `<profile_id>.forecast-plan.json` and `campaign.forecast-plan.json` for the current survivors.
6. `google_keywords.py forecast --plan-file DIR/<id>.forecast-plan.json` for each plan; reference the exports as `forecast_file`.
7. `search_viability.py evaluate` again for the decision. If survivors, budgets, dates, or ceilings change, rerun steps 5–7.

## 0. Lock one offer

Read available product context first. Establish what is sold, price and billing basis, one conversion action, geography/language, and the live page that converts. A purchase, trial, signup, and booked call are different funnel events; select one. Without a named conversion and live page, report INCOMPLETE and identify the missing action. Do not proceed into keyword selection as if the offer were ready.

Inspect the page when available. A URL alone does not prove that it is live, that its message matches a query, or that tracking fires. Record verification evidence; do not perform real purchases or submit leads merely to test tracking without appropriate authorization.

## 1. Money ceiling before keywords

Use account currency consistently. First-order revenue and variable costs must describe the same first payment period as the offer. Include COGS, payment fees, fulfillment, and support time valued at the user's rate. Monthly subscriptions use the first monthly payment, not annual revenue or lifetime value.

For each candidate customer job, calculate:

```text
first_order_contribution = first_order_revenue - variable_costs
contribution_90_days = first_order_contribution
                      + repeat_probability * repeat_contribution
cash_ceiling = first_order_contribution
growth_ceiling = contribution_90_days * acquisition_share
max_cac = min(cash_ceiling, growth_ceiling)
max_cpa = max_cac                         # purchase
max_cpa = max_cac * close_rate            # lead, signup, or trial
max_cpc = max_cpa * landing_conversion_rate
```

`repeat_contribution` means total additional contribution within 90 days **conditional on repeat**, excluding the first payment. Do not multiply an already probability-weighted estimate again. Explicit repeat probability zero requires no additional contribution estimate. Unknown repeat behavior stays unknown until an assumption is supplied.

Default acquisition share is 0.30. Default close rate is 0.20 for non-purchase events; it must mean that exact event's eventual paid-customer rate. Default landing conversion is 0.03 for `cold_saas` or 0.05 for `local_service`. Other pages require an explicit rate. These are conservative starting assumptions, not measured benchmarks or Google requirements. Prefer relevant observed rates and show sensitivity when an assumption changes the conclusion. Do not improve a conversion assumption merely to make a cluster pass.

Use the offline calculator's `economics` command before discovery. It returns READY, NO_GO, or INCOMPLETE. READY means proceed to keyword research; it does not authorize or validate a campaign. Label inputs observed, user_estimated, or default, with evidence when available. Unlabeled supplied inputs are recorded as `supplied_unverified`.

## 2. Profiles as search jobs

Default to three distinct jobs, fewer when the offer only supports fewer. Each needs: outcome wanted this week, reason to pay, search stage, contribution/CAC/CPC ceilings, and disqualifier. Use `ready_to_buy` or `late_solution_aware` for first-test candidates. Early problem awareness belongs in the SEO/content analysis.

## 3. Keywords and negatives together

Generate approximately 10–30 useful terms per job without padding. Seed from the searcher's task, commercial problem modifiers, the offer, or relevant competitor-switching intent. Use historical `metrics` on the prepared list; `ideas` can expand a narrow cluster after economics are established.

Build negatives from disqualifiers before Planner: unrelated meanings, job-seeking, education, unsupported markets/platforms/audiences, and irrelevant informational intent. Review “free”, “DIY”, “template”, and similar terms against the offer; they are not universal exclusions. Record each negative's EXACT/PHRASE/BROAD match type, campaign/ad-group scope, and reason. Check that negatives do not block intended positives, and record the review even when the list is empty. Negative matching does not expand like positive close variants; consider relevant forms explicitly. [Google's negative keyword guidance](https://support.google.com/google-ads/answer/2453972)

Default positives to EXACT on the strongest terms and PHRASE on the rest. Exact still permits close variants. Keep brand terms outside non-brand viability; brand demand cannot establish new-market demand.

## 4. Planner filters the list

Use the exact market/language and Google Search network for historical research. Preserve returned close-variant groups and null values. Never sum duplicate spellings or overlapping batch groups into demand.

Record monthly searches, low/high top-of-page bids, average CPC, and the month comparison. Average CPC is what advertisers paid historically; report it as context, but the gates use the high top-of-page bid as the stress proxy. Idea concepts flag brand terms (`BRAND`/`OTHER_BRANDS`); `scaffold` pre-sets `brand: true` for those, and you still confirm every brand and intent judgment. The calculator compares the latest complete returned month with three months earlier, requiring all four consecutive months. Missing months or a zero starting value produce an unavailable percentage. This is a named derived comparison, not a claim to reproduce a Planner UI field.

Low/high bid estimates are optimistic/stress proxies, not predicted CPC. Google describes them as historical percentile estimates; account/UI data availability can vary, so preserve the values actually returned. [Metric interpretation](https://support.google.com/google-ads/answer/3022575)

Default classification:

- **Keep:** commercial, non-brand, and high bid strictly below Max CPC (a bid equal to the ceiling leaves no margin, matching the strict CPA gate).
- **Park:** unaffordable, ambiguous, or missing bid evidence. Keeping such a term needs a documented override reason.
- **Exclude:** brand or informational intent for this non-brand paid test.

Fewer than 30 monthly searches is a demand flag, not an automatic rejection; evaluate the surviving cluster's actual testability. Never infer zero demand from missing metrics. The default cluster stress CPC is the highest high-bid estimate among survivors. If any is missing, require a reasoned explicit stress CPC or leave the assessment INCOMPLETE.

Each keyword's `match_status` says whether it found exactly one historical row (`matched`), none (`unmatched`), several overlapping groups (`ambiguous`), or no export was supplied (`no_history`). Anything but `matched` leaves the term unpriced and parked; fix the spelling, split the term, rerun `metrics`, or document an override.

Forecast each profile at its allocated daily budget and calculated `forecast_max_cpc`, using explicit future dates. `evaluate --forecast-plans` writes these scenarios exactly; a mismatched export names the differing fields. This cap is Max CPC rounded **down** to whole micros. Read clicks and cost as estimates; derive conversions from the stated funnel assumptions.

The current v25 request supports budgets, CPC caps, and positive match types but cannot accept negatives or a network setting. Results are campaign period totals, without profile-level allocation. Disclose these limitations; do not invent missing controls or forecasts. [v25 definitions](https://raw.githubusercontent.com/googleapis/googleapis/master/google/ads/googleads/v25/services/keyword_plan_idea_service.proto)

If API access is unavailable, continue useful economics and provisional keyword work, label it incomplete, and provide the exact Planner settings needed. Planner UI evidence can inform a manual assessment, but the calculator consumes the documented API exports; never disguise manually entered values as an API response.

## 5. Go / no-go

Default test window: 14 days. The user supplies an affordable daily budget and total loss limit; do not silently raise them to make the test pass. Recommend `10 * stress_cpc` daily and `14 * daily_budget` total as the minimum starting capacity, then compare with what they can actually spend.

```text
purchasable_clicks = min(forecast_period_clicks,
                        min(total_budget, daily_budget * days) / stress_cpc)
stress_spend = purchasable_clicks * stress_cpc
expected_conversions = purchasable_clicks * landing_conversion_rate
implied_cpa = stress_spend / expected_conversions
budget_clicks_per_day = daily_budget / stress_cpc
```

GO requires all gates: offer and positive economics, eligible search job, retained commercial keywords, matching forecast, stress CPA strictly below Max CPA, at least 100 purchasable clicks, capacity for at least 10 clicks/day, and evidenced page fit, tracking, and negative review. Zero clicks is a known failure; missing clicks is unknown. Zero expected conversions has no finite implied CPA.

These thresholds screen whether a test is worth considering. They do not establish statistical power or guarantee learning; 100 clicks at 3% conversion implies only three expected conversions. The calculator's `test.thresholds` overrides need a reason. Economics and stress overrides remain visible in the input and assumptions.

A known failed gate yields NO_GO even if other evidence is missing; list both failures and unknowns. INCOMPLETE means evidence is insufficient to decide, and must name what would resolve it. Explain whether price/margin, auction cost, intent, demand, budget, page fit, or tracking caused the result.

Select profiles explicitly for a combined campaign. Their allocated daily budgets must fit both campaign daily capacity and the total loss limit. Obtain a combined forecast of the survivors using the lowest included CPC ceiling; do not add independent profile forecasts. The combined stress calculation uses the highest stress CPC and lowest conversion rate/CPA ceiling across included profiles. This deliberately conservative envelope may park a combination that works as separate tests. Report that reason instead of silently changing assumptions. A combined GO is conditional on maintaining the planned allocations; live campaign budgets do not reserve spend per ad group.

## 6. Passing test handoff

Return a reviewable brief with one non-brand Search campaign, one ad group per passing profile, positive match types, shared and group negatives, landing pages, selected conversion, CPC ceilings, and budget allocations. Default to Manual CPC for distinct profile ceilings; capped Maximize Clicks requires the lowest common ceiling. Propose partners and Display off.

State the total loss limit, dates, and enforcement mechanism. Use an eligible campaign total budget with start/end dates for a hard test cap; an average daily budget alone does not enforce a 14-day total. If that setup is unavailable, flag the limitation and require a concrete spending-control arrangement in the launch handoff. [Google campaign budgets](https://developers.google.com/google-ads/api/docs/campaigns/budgets/overview)

Propose search-term reviews on days 3 and 7, adding negatives after review. Review on day 14 and stop further spend at the loss limit/end date. After at least 100 clicks, pause an ad group when mature-conversion CPA exceeds 1.5× Max CPA; with spend and zero mature conversions it has no finite CPA. Account for conversion delay before judging outcomes, without extending spend automatically. Review actual allocation so one group cannot consume the others' test budgets unnoticed.

About 30 recent conversions can prompt a bidding-strategy review. It is not a target CPA eligibility requirement, nor automatic permission to use broad match. [Google target CPA guidance](https://support.google.com/google-ads/answer/6268632)

Do not create campaigns, alter tracking, or schedule reviews merely because research passed. Provide the brief and proposed dates; execution is a separate task.

## Deliverables and calculator contract

Use [viability-calculator.md](viability-calculator.md) for input fields, commands, and a complete example. Deliver one decision CSV (profiles plus campaign), reusable input/result JSON, keyword/negative CSVs, and a short explanation of the decision, assumptions, failed gates, and next action. Retain raw exports separately; the calculator also snapshots referenced evidence in its JSON. Include geography, language, currency, network limitations, retrieval dates, forecast dates, and overrides. Do not treat a profile GO as a campaign GO.
