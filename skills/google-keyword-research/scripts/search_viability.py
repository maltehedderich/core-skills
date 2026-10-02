#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Offline Search Viability Loop. Run with: uv run search_viability.py --help."""
import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULTS = {"test_days": 14, "min_clicks": 100, "min_daily_clicks": 10, "low_volume": 30}
STRATEGIES = {"manual_cpc", "maximize_clicks"}
PARK_REASONS = {"no_history": "No historical export; add historical_file or override",
                "unmatched": "No historical match; check the spelling against the export or override",
                "ambiguous": "Ambiguous historical match; split or override"}


def number(value, name, *, rate=False):
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            raise ValueError()
        result = Decimal(str(value))
        if not result.is_finite() or (rate and not 0 <= result <= 1):
            raise ValueError()
        return result
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be finite" + (" and between 0 and 1" if rate else "")) from None


def nonnegative(value, name):
    result = number(value, name)
    if result is not None and result < 0:
        raise ValueError(f"{name} cannot be negative")
    return result


def gate(value, reason):
    return {"passed": value, "reason": reason}


def combine(values):
    """A known failure outranks unknowns; everything must pass to pass."""
    if False in values:
        return False
    return None if None in values else True


def status(gates):
    return {True: "GO", None: "INCOMPLETE", False: "NO_GO"}[combine([g["passed"] for g in gates.values()])]


def bid_cap(value):
    return value.quantize(Decimal("0.000001"), rounding=ROUND_FLOOR) if value is not None else None


def verified(item):
    if not isinstance(item, dict):
        return None
    if item.get("verified") is False:
        return False
    return True if item.get("verified") is True and isinstance(item.get("evidence"), str) and item["evidence"].strip() else None


def offer_gate(brief):
    offer, market = brief.get("offer", {}), brief.get("market", {})
    required = ("name", "price", "billing_basis", "conversion_action", "conversion_type", "landing_page_url")
    complete = all(offer.get(k) is not None and str(offer[k]).strip() for k in required)
    if offer.get("conversion_type") not in {"purchase", "lead", "trial", "signup"}:
        complete = False
    price = nonnegative(offer.get("price"), "offer.price")
    url = urlsplit(offer.get("landing_page_url", ""))
    complete = complete and price is not None and url.scheme in {"http", "https"} and bool(url.hostname) and not url.username and not url.password
    geo = market.get("geo_ids", [])
    if not isinstance(geo, list) or any(not isinstance(v, str) or not re.fullmatch(r"[1-9]\d*", v) for v in geo):
        raise ValueError("market.geo_ids must be a list of numeric strings")
    complete = complete and bool(geo) != bool(market.get("worldwide", False))
    complete = complete and bool(re.fullmatch(r"[1-9]\d*", str(market.get("language_id", ""))))
    complete = complete and bool(re.fullmatch(r"[A-Z]{3}", market.get("currency_code", "")))
    live = verified(offer.get("landing_page_live"))
    return gate(False if live is False else True if complete and live is True else None,
                "One priced offer, conversion, market, billing basis, and evidenced live page are required.")


def economics(profile, brief):
    raw = profile.get("economics", {})
    sources = profile.get("sources", {})
    assumptions = {}

    def get(key, default=None, rate=False):
        value = raw.get(key)
        defaulted = value is None and default is not None
        if defaulted:
            value = default
        source = sources.get(key, {})
        if not isinstance(source, dict):
            raise ValueError("Each sources entry must have source and optional evidence fields")
        assumptions[key] = {"value": value, "source": "default" if defaulted else source.get("source", "supplied_unverified"),
                            "evidence": source.get("evidence")}
        return number(value, key, rate=rate)

    revenue, costs = get("first_order_revenue"), get("variable_costs")
    if (revenue is not None and revenue < 0) or (costs is not None and costs < 0):
        raise ValueError("Revenue and variable costs cannot be negative")
    repeat = get("repeat_probability", rate=True)
    extra = get("repeat_contribution", 0 if repeat == 0 else None)
    share = get("acquisition_share", "0.30", rate=True)
    page_type = raw.get("page_type")
    cvr = get("landing_conversion_rate", {"cold_saas": "0.03", "local_service": "0.05"}.get(page_type), rate=True)
    purchase = brief.get("offer", {}).get("conversion_type") == "purchase"
    close = Decimal(1) if purchase else get("close_rate", "0.20", rate=True)
    contribution = revenue - costs if revenue is not None and costs is not None else None
    ninety = contribution + repeat * extra if contribution is not None and repeat is not None and extra is not None else None
    growth = ninety * share if ninety is not None else None
    cac = min(contribution, growth) if contribution is not None and growth is not None else None
    cpa = cac * close if cac is not None and close is not None else None
    cpc = cpa * cvr if cpa is not None and cvr is not None else None
    gates = {"offer": offer_gate(brief),
             "billing_basis": gate(True if raw.get("billing_basis") and raw["billing_basis"] == brief.get("offer", {}).get("billing_basis") else None,
                                   "First-order economics must use the offer's billing basis, not lifetime revenue."),
             "positive_contribution": gate(None if contribution is None else contribution > 0, "First-order contribution must be positive."),
             "economics_complete": gate(None if cpc is None else cpc > 0, "Need contribution, expected repeat contribution, and both funnel rates.")}
    return {"id": profile["id"], "first_order_contribution": contribution, "contribution_90_days": ninety,
            "cash_ceiling": contribution, "growth_ceiling": growth, "max_cac": cac, "max_cpa": cpa, "max_cpc": cpc,
            "forecast_max_cpc": bid_cap(cpc), "landing_conversion_rate": cvr, "close_rate": close,
            "assumptions": assumptions, "gates": gates, "status": "READY" if status(gates) == "GO" else status(gates)}


def today(brief):
    """Today in the account timezone when market.time_zone is set, else local time."""
    zone = brief.get("market", {}).get("time_zone")
    if zone is None:
        return date.today()
    try:
        return datetime.now(ZoneInfo(zone)).date()
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ValueError("market.time_zone must be an IANA time zone such as Europe/Berlin") from None


def trend(months, as_of):
    # Require a consecutive four-month window ending before the retrieval month.
    values = {}
    for entry in months:
        month = date.fromisoformat(entry["month"] + "-01")
        if (month.year, month.month) < (as_of.year, as_of.month):
            values[month.year * 12 + month.month - 1] = nonnegative(entry.get("searches"), "monthly searches")
    if not values:
        return {"from": None, "to": None, "percent": None}
    latest = max(values)
    label = lambda index: f"{index // 12:04d}-{index % 12 + 1:02d}"
    window = [values.get(index) for index in range(latest - 3, latest + 1)]
    pct = (window[-1] / window[0] - 1) * 100 if all(v is not None for v in window) and window[0] > 0 else None
    return {"from": label(latest - 3), "to": label(latest), "percent": pct}


def load_export(path, base, evidence):
    if not path:
        return None
    resolved = (base / path).resolve()
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise ValueError(f"Cannot read evidence export: {path}") from None
    if not isinstance(value, dict):
        raise ValueError("Evidence exports must be JSON objects")
    evidence[str(resolved)] = value
    return value


def same_market(export, brief, *, forecast=False):
    market = brief.get("market", {})
    request = export.get("request", {})
    return (export.get("account", {}).get("currency_code") == market.get("currency_code")
            and set(request.get("geo_ids", [])) == set(market.get("geo_ids", []))
            and bool(request.get("worldwide", False)) == bool(market.get("worldwide", False))
            and request.get("language_id") == market.get("language_id")
            and (forecast or request.get("network") == market.get("network", "google")))


def default_decision(item, commercial, affordable):
    if item.get("brand") is True or item.get("commercial_intent") is False:
        return "exclude"
    return "keep" if commercial and affordable else "park"


def match_status(historical, matches):
    if historical is None:
        return "no_history"
    return {0: "unmatched", 1: "matched"}.get(len(matches), "ambiguous")


def survivor_state(selected):
    if any(row["decision"] == "keep" for row in selected):
        return True
    if not selected or any(row["selection_unresolved"] for row in selected):
        return None
    return False


def keywords(profile, historical, brief, result, thresholds):
    if historical and (historical.get("command") not in {"ideas", "metrics"} or not same_market(historical, brief)):
        raise ValueError("Historical export command, currency, or market does not match the brief")
    rows = historical.get("results", []) if historical else []
    as_of = date.fromisoformat(historical["retrieved_at"][:10]) if historical else date.today()
    output = []
    seen = set()
    for item in profile.get("keywords", []):
        text = item.get("keyword", "").strip()
        match = item.get("match_type")
        if not text or match not in {"EXACT", "PHRASE"}:
            raise ValueError("Keywords require keyword and EXACT or PHRASE match_type")
        key = (text.casefold(), match)
        if key in seen:
            raise ValueError("Duplicate keyword/match type in a profile")
        seen.add(key)
        matches = [(i, row) for i, row in enumerate(rows) if text.casefold() in {s.casefold() for s in [row["keyword"], *row.get("close_variants", [])]}]
        index, row = matches[0] if len(matches) == 1 else (None, {})
        matched = match_status(historical, matches)
        low = nonnegative(row.get("low_top_of_page_bid"), "low bid")
        high = nonnegative(row.get("high_top_of_page_bid"), "high bid")
        volume = nonnegative(row.get("avg_monthly_searches"), "monthly searches")
        commercial = item.get("commercial_intent") is True and item.get("brand") is False
        # Strict, like the affordable_cpa gate: a bid equal to Max CPC leaves no margin.
        affordable = high is not None and result["max_cpc"] is not None and high < result["max_cpc"]
        unresolved = item.get("commercial_intent") is None or item.get("brand") is None or high is None or result["max_cpc"] is None
        default = default_decision(item, commercial, affordable)
        default_reason = {"keep": "Commercial and below CPC ceiling", "park": PARK_REASONS.get(matched, "Affordability or intent unresolved"),
                          "exclude": "Brand or informational intent"}[default]
        decision = item.get("decision", default)
        if decision not in {"keep", "park", "exclude"}:
            raise ValueError("Keyword decision must be keep, park, or exclude")
        if decision == "keep" and not commercial:
            raise ValueError("Kept keywords require commercial_intent: true and brand: false")
        if decision == "keep" and default != "keep" and not item.get("override_reason"):
            raise ValueError("Keeping an unpriced or unaffordable keyword requires override_reason")
        output.append({"profile_id": profile["id"], "keyword": text, "match_type": match, "decision": decision,
                       "reason": item.get("reason") or default_reason,
                       "override_reason": item.get("override_reason"), "historical_group": index, "match_status": matched,
                       "selection_unresolved": decision == "park" and unresolved,
                       "close_variants": row.get("close_variants", []), "avg_monthly_searches": volume,
                       "low_top_of_page_bid": low, "high_top_of_page_bid": high,
                       "average_cpc": nonnegative(row.get("average_cpc"), "average CPC"), "concepts": row.get("concepts"),
                       "low_volume_flag": None if volume is None else volume < thresholds["low_volume"],
                       "trend": trend(row.get("monthly_search_volumes", []), as_of)})
    return output


def forecast_plan(brief, test, groups, daily_budget, cap):
    """Return (plan, None) in google_keywords.py forecast --plan-file format, or (None, reason)."""
    market = brief.get("market", {})
    if not groups or any(not g["keywords"] for g in groups):
        return None, "no kept keywords"
    if not test.get("start_date") or not test.get("end_date"):
        return None, "no test dates"
    if daily_budget is None or daily_budget <= 0:
        return None, "no daily budget"
    if cap is None or bid_cap(cap) <= 0:
        return None, "no positive CPC ceiling"
    if not market.get("currency_code") or not market.get("language_id") or bool(market.get("geo_ids")) == bool(market.get("worldwide", False)):
        return None, "incomplete market"
    plan = {"currency_code": market["currency_code"]}
    plan.update({"worldwide": True} if market.get("worldwide") else {"geo_ids": list(market["geo_ids"])})
    plan.update(language_id=market["language_id"], start_date=test["start_date"], end_date=test["end_date"],
                daily_budget=str(daily_budget), max_cpc=str(bid_cap(cap)), bidding_strategy=test.get("bidding_strategy", "manual_cpc"),
                ad_groups=[{"id": g["id"], "keywords": [dict(k) for k in g["keywords"]]} for g in groups])
    return plan, None


def keyword_sets(groups):
    return {g.get("id"): {(k.get("text", "").strip().casefold(), k.get("match_type")) for k in g.get("keywords", [])} for g in groups}


def forecast_mismatches(export, request, plan, test):
    """Name every scenario dimension where a forecast export differs from the expected plan."""
    actual_groups = request.get("ad_groups", [])
    checks = {"command": export.get("command") == "forecast",
              "metrics_basis": export.get("metrics_basis") == "period_total",
              "currency_code": export.get("account", {}).get("currency_code") == request.get("currency_code") == plan["currency_code"],
              "geo_ids": set(request.get("geo_ids", [])) == set(plan.get("geo_ids", [])),
              "worldwide": bool(request.get("worldwide", False)) == plan.get("worldwide", False),
              "language_id": request.get("language_id") == plan["language_id"],
              "start_date": request.get("start_date") == plan["start_date"],
              "end_date": request.get("end_date") == plan["end_date"],
              "daily_budget": number(request.get("daily_budget"), "forecast daily budget") == Decimal(plan["daily_budget"]),
              "max_cpc": number(request.get("max_cpc"), "forecast CPC cap") == Decimal(plan["max_cpc"]),
              # An undeclared test strategy accepts either click strategy, as before.
              "bidding_strategy": request.get("bidding_strategy") == plan["bidding_strategy"] if "bidding_strategy" in test
                                  else request.get("bidding_strategy") in STRATEGIES,
              "ad_groups": keyword_sets(actual_groups) == keyword_sets(plan["ad_groups"]) and len(actual_groups) == len(plan["ad_groups"])}
    return [name for name, ok in checks.items() if not ok]


def forecast_clicks(export, brief, test, groups, daily_budget, cap, gates, name):
    plan, missing = forecast_plan(brief, test, groups, daily_budget, cap)
    if export is None:
        gates["forecast"] = gate(None, "A matching read-only forecast export is required." + (f" Run forecast with {name}.forecast-plan.json from evaluate --forecast-plans." if plan else ""))
        return None
    if plan is None:
        gates["forecast"] = gate(None, f"Cannot check the forecast: {missing}.")
        return None
    differences = forecast_mismatches(export, export.get("request", {}), plan, test)
    if differences:
        gates["forecast"] = gate(None, f"Forecast mismatch: {', '.join(differences)}; rerun forecast with {name}.forecast-plan.json from evaluate --forecast-plans.")
        return None
    clicks = nonnegative(export.get("results", {}).get("clicks"), "forecast clicks")
    gates["forecast"] = gate(True if clicks is not None else None, "Use campaign period totals; network and negatives are not modeled by v25.")
    return clicks


def evaluate_budget(result, *, clicks, daily, total, days, stress, cvr, cpa, thresholds):
    gates = result["gates"]
    ready = all(v is not None for v in (clicks, daily, total, days, stress, cvr, cpa)) and stress > 0
    bought = min(clicks, min(total, daily * days) / stress) if ready else None
    spend = bought * stress if bought is not None else None
    conversions = bought * cvr if bought is not None else None
    implied = spend / conversions if conversions is not None and conversions > 0 else None
    capacity = daily / stress if daily is not None and stress is not None and stress > 0 else None
    result.update(stress_cpc=stress, daily_budget=daily, total_budget=total, forecast_clicks=clicks, purchasable_clicks=bought,
                  stress_spend=spend, expected_conversions=conversions, implied_cpa=implied, budget_clicks_per_day=capacity)
    gates["affordable_cpa"] = gate(None if stress is None or cpa is None or cvr is None else cvr > 0 and stress / cvr < cpa,
                                   "Stress CPC / conversion rate must be strictly below Max CPA.")
    gates["test_clicks"] = gate(None if bought is None else bought >= thresholds["min_clicks"], "Forecast and budget must support the minimum test clicks.")
    gates["daily_capacity"] = gate(None if capacity is None else capacity >= thresholds["min_daily_clicks"], "Daily budget must cover the minimum clicks at stress CPC.")
    result["status"] = status(gates)


def run(brief, mode, base):
    profiles = brief.get("profiles", [])
    if not isinstance(profiles, list) or not profiles or any(not isinstance(p.get("id"), str) or not p["id"] for p in profiles):
        raise ValueError("Provide profiles with nonempty string IDs")
    if len({p["id"] for p in profiles}) != len(profiles) or any(p["id"] == "campaign" for p in profiles):
        raise ValueError("Profile IDs must be unique and cannot be 'campaign'")
    results = [economics(p, brief) for p in profiles]
    output = {"schema_version": 1, "command": mode, "retrieved_at": datetime.now(timezone.utc).isoformat(),
              "currency_code": brief.get("market", {}).get("currency_code"), "inputs": brief, "profiles": results,
              "evidence": {}, "keywords": [], "negatives": [], "warnings": ["Default rates and click thresholds are planning assumptions, not benchmarks or statistical guarantees."]}
    if mode == "economics":
        return output
    test = brief.get("test", {})
    thresholds = dict(DEFAULTS)
    overrides = test.get("thresholds", {})
    if set(overrides) - set(DEFAULTS):
        raise ValueError("Unknown threshold override")
    if overrides and not test.get("override_reason"):
        raise ValueError("Threshold overrides require test.override_reason")
    for name, value in overrides.items():
        amount = number(value, name)
        if amount is None or amount <= 0 or amount != amount.to_integral_value():
            raise ValueError("Thresholds must be positive integers")
        thresholds[name] = int(amount)
    output["thresholds"] = thresholds
    start, end = test.get("start_date"), test.get("end_date")
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 if start and end else None
    if days is not None and days <= 0:
        raise ValueError("Test dates must be ordered")
    if days is not None and days != thresholds["test_days"] and not test.get("override_reason"):
        raise ValueError("A non-default test duration requires test.override_reason")
    if test.get("bidding_strategy", "manual_cpc") not in STRATEGIES:
        raise ValueError("test.bidding_strategy must be manual_cpc or maximize_clicks")
    date_ready = True if start and end and date.fromisoformat(start) > today(brief) else None
    total = nonnegative(test.get("total_budget"), "total budget")
    daily = nonnegative(test.get("daily_budget"), "daily budget")
    by_id = {}
    for profile, result in zip(profiles, results):
        by_id[profile["id"]] = (profile, result)
        gates = result["gates"]
        gates["test_dates"] = gate(date_ready, "Use an explicit future test window; refresh an expired plan before launch.")
        gates["search_job"] = gate(True if all(profile.get(k) for k in ("job", "why_pay", "disqualifier")) else None, "Describe the search job, reason to pay, and disqualifier.")
        stage = profile.get("search_stage")
        gates["search_stage"] = gate(None if stage is None else stage in {"ready_to_buy", "late_solution_aware"}, "Only late commercial jobs enter the first test.")
        history = load_export(profile.get("historical_file"), base, output["evidence"])
        selected = keywords(profile, history, brief, result, thresholds)
        output["keywords"].extend(selected)
        kept = [row for row in selected if row["decision"] == "keep"]
        gates["surviving_keywords"] = gate(survivor_state(selected), "At least one retained non-brand commercial keyword is required; unpriced candidates remain unresolved.")
        highs = [row["high_top_of_page_bid"] for row in kept]
        stress = max(highs) if highs and all(v is not None for v in highs) else None
        if profile.get("stress_cpc") is not None:
            if not profile.get("stress_cpc_reason"):
                raise ValueError("A supplied stress CPC requires stress_cpc_reason")
            stress = nonnegative(profile["stress_cpc"], "stress CPC")
        if stress is not None and stress <= 0:
            stress = None
        group = {"id": profile["id"], "keywords": [{"text": r["keyword"], "match_type": r["match_type"]} for r in kept]}
        result["forecast_group"] = group
        allocation = nonnegative(profile.get("daily_budget"), "profile daily budget")
        forecast = load_export(profile.get("forecast_file"), base, output["evidence"])
        clicks = forecast_clicks(forecast, brief, test, [group], allocation, result["max_cpc"], gates, profile["id"])
        readiness = profile.get("readiness", {})
        for name in ("landing_page_match", "tracking"):
            gates[name] = gate(verified(readiness.get(name)), "Need verified evidence for " + name.replace("_", " ") + ".")
        gates["negative_review"] = gate(verified(profile.get("negative_review")), "Review disqualifiers and conflicts before forecasting; an empty list requires evidence too.")
        for item in profile.get("negatives", []):
            if not item.get("keyword") or item.get("match_type") not in {"EXACT", "PHRASE", "BROAD"} or item.get("scope") not in {"campaign", "ad_group"} or not item.get("reason"):
                raise ValueError("Negatives require keyword, match_type, scope, and reason")
            output["negatives"].append({"profile_id": profile["id"], **item})
        allocation_total = allocation * days if allocation is not None and days is not None else None
        evaluate_budget(result, clicks=clicks, daily=allocation, total=allocation_total, days=days, stress=stress,
                        cvr=result["landing_conversion_rate"], cpa=result["max_cpa"], thresholds=thresholds)
    campaign = {"id": "campaign", "gates": {}}
    campaign["gates"]["test_dates"] = gate(date_ready, "Use an explicit future test window.")
    output["campaign"] = campaign
    ids = brief.get("campaign", {}).get("profile_ids", [])
    if len(ids) != len(set(ids)) or any(i not in by_id for i in ids):
        raise ValueError("campaign.profile_ids must name unique existing profiles")
    if not ids:
        campaign["gates"]["selected_profiles"] = gate(None, "Select passing profiles and supply a combined forecast; profile forecasts cannot be added.")
        campaign["status"] = "INCOMPLETE"
        return output
    selected = [by_id[i][1] for i in ids]
    campaign["gates"]["selected_profiles"] = gate(combine([{"GO": True, "NO_GO": False}.get(r["status"]) for r in selected]), "Every included profile must pass its own gates.")
    allocations = [r["daily_budget"] for r in selected]
    allocation_sum = sum(allocations) if all(v is not None for v in allocations) else None
    campaign["gates"]["budget_allocations"] = gate(None if allocation_sum is None or daily is None or total is None or days is None else allocation_sum <= daily and allocation_sum * days <= total,
                                                       "Included profile budgets must fit both campaign daily and total loss limits.")
    caps, stresses = [r["max_cpc"] for r in selected], [r["stress_cpc"] for r in selected]
    rates, cpas = [r["landing_conversion_rate"] for r in selected], [r["max_cpa"] for r in selected]
    minimum = lambda values: min(values) if all(v is not None for v in values) else None
    cap, cvr, cpa = minimum(caps), minimum(rates), minimum(cpas)
    stress = max(stresses) if all(v is not None for v in stresses) else None
    campaign.update(max_cpc=cap, forecast_max_cpc=bid_cap(cap), max_cpa=cpa, landing_conversion_rate=cvr, profile_ids=ids)
    forecast = load_export(brief.get("campaign", {}).get("forecast_file"), base, output["evidence"])
    clicks = forecast_clicks(forecast, brief, test, [r["forecast_group"] for r in selected], daily, cap, campaign["gates"], "campaign")
    evaluate_budget(campaign, clicks=clicks, daily=daily, total=total, days=days, stress=stress, cvr=cvr, cpa=cpa, thresholds=thresholds)
    output["warnings"].append("Combined stress scenario uses the highest CPC and lowest conversion rate/CPA ceiling across selected profiles; it is conservative, not an allocation forecast.")
    return output


def encode_decimal(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Cannot encode {type(value).__name__}")


def json_text(value):
    return json.dumps(value, indent=2, ensure_ascii=False, default=encode_decimal) + "\n"


def csv_text(rows):
    rows = [{k: json.dumps(v, default=str, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()} for row in rows]
    fields = list(dict.fromkeys(k for row in rows for k in row)) or ["id"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: escape_formula(v) for k, v in row.items()})
    return stream.getvalue()


def escape_formula(value):
    """Prevent spreadsheet formula execution for untrusted strings."""
    if isinstance(value, str) and (value.startswith(("\t", "\r")) or value.lstrip().startswith(("=", "+", "-", "@"))):
        return "'" + value
    return value


def decision_rows(data):
    rows = []
    results = [*data["profiles"], *([data["campaign"]] if "campaign" in data else [])]
    test = data["inputs"].get("test", {})
    for result in results:
        market = data["inputs"].get("market", {})
        row = {"id": result["id"], "status": result["status"], "currency_code": data["currency_code"],
               "geo_ids": market.get("geo_ids", []), "worldwide": market.get("worldwide", False),
               "language_id": market.get("language_id"), "historical_network": market.get("network", "google"),
               "retrieved_at": data["retrieved_at"], "start_date": test.get("start_date"), "end_date": test.get("end_date"),
               "forecast_limitations": "v25 does not model negatives or network settings; campaign totals only" if data["command"] == "evaluate" else None}
        row.update({k: v for k, v in result.items() if k not in {"forecast_group", "assumptions", "gates"}})
        row.update({f"gate_{name}": check["passed"] for name, check in result["gates"].items()})
        row["failed_gates"] = "; ".join(name for name, check in result["gates"].items() if check["passed"] is False)
        row["unknown_gates"] = "; ".join(name for name, check in result["gates"].items() if check["passed"] is None)
        row["required_actions"] = " ".join(check["reason"] for check in result["gates"].values() if check["passed"] is not True)
        rows.append(row)
    return rows


def plan_targets(data):
    """Yield (id, plan, skip_reason) for every profile and the campaign, from the same inputs evaluate checks."""
    brief, test = data["inputs"], data["inputs"].get("test", {})
    groups = {r["id"]: r["forecast_group"] for r in data["profiles"]}
    for result in data["profiles"]:
        yield (result["id"], *forecast_plan(brief, test, [result["forecast_group"]], result["daily_budget"], result["max_cpc"]))
    campaign = data["campaign"]
    if not campaign.get("profile_ids"):
        yield "campaign", None, "no campaign.profile_ids selected"
    else:
        yield ("campaign", *forecast_plan(brief, test, [groups[i] for i in campaign["profile_ids"]], campaign["daily_budget"], campaign["max_cpc"]))


def scaffold(historical, profile_id, reference, brief=None):
    """Turn an ideas/metrics export into profile keyword entries for the agent to judge."""
    if historical.get("command") not in {"ideas", "metrics"}:
        raise ValueError("scaffold needs an ideas or metrics export")
    if brief is not None and not same_market(historical, brief):
        raise ValueError("Historical export currency or market does not match the brief")
    entries, seen = [], set()
    for row in historical.get("results", []):
        text = str(row.get("keyword") or "").strip()
        if not text or text.casefold() in seen:
            continue
        seen.add(text.casefold())
        concepts = row.get("concepts")
        # Concepts are a hint only: a brand group marks brand, anything else stays for the agent to judge.
        brand = True if any(c.get("group_type") in ("BRAND", "OTHER_BRANDS") for c in concepts or []) else None
        entries.append({"keyword": text, "match_type": "PHRASE", "commercial_intent": None, "brand": brand,
                        "avg_monthly_searches": row.get("avg_monthly_searches"), "high_top_of_page_bid": row.get("high_top_of_page_bid"),
                        "average_cpc": row.get("average_cpc"), "concepts": concepts})
    return {"id": profile_id, "historical_file": reference, "keywords": entries}


def summary(command, data, outputs):
    """Compact TSV for stdout when full JSON goes to a file."""
    lines = [f"command={command}\toutputs={','.join(str(p) for p in outputs)}"]
    if command == "scaffold":
        brand = sum(1 for k in data["keywords"] if k["brand"])
        lines[0] += f"\tprofile={data['id']}\tkeywords={len(data['keywords'])}\tbrand_hints={brand}"
        return lines[0] + "\n"
    lines.append("id\tstatus\tmax_cpc\tfailed_gates\tunknown_gates")
    for row in decision_rows(data):
        lines.append("\t".join("" if row.get(k) is None else str(row[k]) for k in ("id", "status", "max_cpc", "failed_gates", "unknown_gates")))
    for entry in data.get("forecast_plans", []):
        lines.append(f"forecast_plan\t{entry['id']}\t" + (entry["path"] or f"skipped: {entry['skipped']}"))
    return "\n".join(lines) + "\n"


def atomic_write(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("economics", "evaluate", "scaffold"))
    parser.add_argument("--input", type=Path, help="Brief/plan JSON; required for economics and evaluate, optional market check for scaffold")
    parser.add_argument("--output", type=Path, help="JSON file; stdout then gets a compact summary")
    parser.add_argument("--csv", type=Path, help="Decision sheet")
    parser.add_argument("--keywords-csv", type=Path)
    parser.add_argument("--negatives-csv", type=Path)
    parser.add_argument("--forecast-plans", type=Path, metavar="DIR", help="evaluate: write <profile_id>.forecast-plan.json and campaign.forecast-plan.json")
    parser.add_argument("--historical", type=Path, help="scaffold: ideas or metrics export")
    parser.add_argument("--profile-id", help="scaffold: profile ID for the emitted entries")
    args = parser.parse_args(argv)
    if args.command == "scaffold":
        if not args.historical or not args.profile_id:
            parser.error("scaffold requires --historical and --profile-id")
        if args.csv or args.keywords_csv or args.negatives_csv or args.forecast_plans:
            parser.error("scaffold writes JSON only; use --output")
    else:
        if not args.input:
            parser.error(f"{args.command} requires --input")
        if args.historical or args.profile_id:
            parser.error("--historical and --profile-id belong to scaffold")
        if args.forecast_plans and args.command != "evaluate":
            parser.error("--forecast-plans requires evaluate")
    try:
        brief = json.loads(args.input.read_text(encoding="utf-8")) if args.input else None
        plans = []
        if args.command == "scaffold":
            if not args.profile_id.strip() or args.profile_id == "campaign":
                raise ValueError("--profile-id must be nonempty and not 'campaign'")
            evidence = {}
            historical = load_export(str(args.historical), Path.cwd(), evidence)
            reference = os.path.relpath(next(iter(evidence)), args.input.resolve().parent) if args.input else str(args.historical)
            data = scaffold(historical, args.profile_id, reference, brief)
            inputs = {Path(p) for p in evidence} | ({args.input.resolve()} if args.input else set())
        else:
            data = run(brief, args.command, args.input.resolve().parent)
            inputs = {args.input.resolve(), *(Path(p) for p in data["evidence"])}
        if args.forecast_plans:
            if not args.forecast_plans.is_dir():
                raise ValueError("--forecast-plans must name an existing directory")
            data["forecast_plans"] = []
            for name, plan, reason in plan_targets(data):
                if plan is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
                    raise ValueError(f"Profile ID {name!r} cannot be used as a file name; use letters, digits, '.', '_', or '-'")
                path = args.forecast_plans / f"{name}.forecast-plan.json" if plan is not None else None
                data["forecast_plans"].append({"id": name, "path": str(path) if path else None, "skipped": reason})
                if path:
                    plans.append((path, plan))
        outputs = [p.resolve() for p in (args.output, args.csv, args.keywords_csv, args.negatives_csv, *(path for path, _ in plans)) if p]
        if len(outputs) != len(set(outputs)) or inputs.intersection(outputs):
            raise ValueError("Output paths must differ and must not overwrite input or evidence files")
        if any(not p.parent.is_dir() or p.is_dir() for p in outputs):
            raise ValueError("Output paths must name files in existing directories")
        rendered = json_text(data)
        exports = [(path, json_text(plan)) for path, plan in plans]
        if args.command != "scaffold":
            exports += [(args.csv, csv_text(decision_rows(data))), (args.keywords_csv, csv_text(data["keywords"])), (args.negatives_csv, csv_text(data["negatives"]))]
        for path, content in exports:
            if path:
                atomic_write(path, content)
        if args.output:
            atomic_write(args.output, rendered)
            print(summary(args.command, data, [p for p in (args.output, args.csv, args.keywords_csv, args.negatives_csv) if p]), end="")
        else:
            print(rendered, end="")
        return 0
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
