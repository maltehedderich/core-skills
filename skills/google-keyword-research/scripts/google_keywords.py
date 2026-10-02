#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-ads>=32,<33"]
# ///
"""Read-only Google Ads keyword research. Run with: uv run google_keywords.py --help."""

import argparse
import csv
import io
import json
import logging
import os
import random
import re
import sys
import tempfile
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

API_VERSION = "v25"


class UserError(Exception):
    """An actionable error safe to show without credential or request contents."""


def api_error(exc):
    """Return safe enum codes, never raw server messages or exception strings."""
    from google.ads.googleads.errors import GoogleAdsException
    from google.api_core import exceptions

    if isinstance(exc, GoogleAdsException):
        codes = []
        for error in exc.failure.errors:
            proto = error.error_code._pb
            field = proto.WhichOneof("error_code")
            if field:
                number = getattr(proto, field)
                enum = proto.DESCRIPTOR.fields_by_name[field].enum_type
                codes.append(enum.values_by_number[number].name)
        retryable = bool(codes) and all(
            code in {"RESOURCE_EXHAUSTED", "RESOURCE_TEMPORARILY_EXHAUSTED", "INTERNAL_ERROR", "TRANSIENT_ERROR"}
            for code in codes
        )
        request_id = exc.request_id or "unknown"
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id):
            request_id = "redacted"
        return retryable, f"Google Ads error: {', '.join(codes) or 'UNKNOWN'}; request ID: {request_id}."
    if isinstance(exc, (exceptions.ResourceExhausted, exceptions.ServiceUnavailable, exceptions.DeadlineExceeded, exceptions.InternalServerError)):
        return True, f"Google API error: {type(exc).__name__}."
    return False, f"Request failed ({type(exc).__name__})."


class Calls:
    def __init__(self, sleep=time.sleep, clock=time.monotonic):
        self.sleep, self.clock = sleep, clock
        self.last_planning = None

    def run(self, call, planning=False):
        for attempt in range(3):
            if planning and self.last_planning is not None:
                self.sleep(max(0, 1.05 - (self.clock() - self.last_planning)))
            if planning:
                self.last_planning = self.clock()
            try:
                return call()
            except Exception as exc:
                retryable, message = api_error(exc)
                if not retryable or attempt == 2:
                    raise UserError(message + " Check OAuth credentials, customer access, Cloud project Basic/Standard access, and quotas; see references/setup.md.") from None
                self.sleep(2 ** attempt + random.uniform(0, 0.25))


def customer_id(value):
    value = value.replace("-", "")
    if not re.fullmatch(r"\d{10}", value):
        raise argparse.ArgumentTypeError("customer ID must contain 10 digits (hyphens allowed)")
    return value


def positive_id(value):
    if not re.fullmatch(r"[1-9]\d*", value):
        raise argparse.ArgumentTypeError("use a positive Google target ID")
    return value


def year_month(value):
    match = re.fullmatch(r"(\d{4})-(0[1-9]|1[0-2])", value)
    if not match:
        raise argparse.ArgumentTypeError("use YYYY-MM")
    return int(match[1]), int(match[2])


def positive_int(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return result


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("ideas", "metrics", "forecast", "locations", "languages", "doctor"):
        p = sub.add_parser(name)
        p.add_argument("--customer-id", type=customer_id, required=True)
        p.add_argument("--config", type=Path, help="External Google Ads YAML; otherwise use GOOGLE_ADS_* environment variables")
        p.add_argument("--output", type=Path, help="JSON file; defaults to stdout")
        if name in ("ideas", "metrics", "doctor"):
            p.add_argument("--keyword", action="append", default=[])
            p.add_argument("--keywords-file", type=Path, help="UTF-8, one keyword per line")
            geo = p.add_mutually_exclusive_group(required=name != "doctor")
            geo.add_argument("--geo-id", type=positive_id, action="append")
            geo.add_argument("--worldwide", action="store_true")
            p.add_argument("--language-id", type=positive_id, required=name != "doctor")
            p.add_argument("--network", choices=("google", "google-and-partners"), default="google")
            p.add_argument("--from-month", type=year_month, help="First month (YYYY-MM) of a custom historical window")
            p.add_argument("--to-month", type=year_month, help="Last month (YYYY-MM) of a custom historical window; before the current month")
        if name in ("ideas", "metrics", "forecast"):
            p.add_argument("--csv", type=Path, help="Optional spreadsheet export")
        if name == "forecast":
            p.add_argument("--plan-file", type=Path, required=True, help="Forecast scenario JSON; see references/cli-and-metrics.md")
        if name == "ideas":
            p.add_argument("--url", help="HTTP(S) page URL seed")
            p.add_argument("--site", help="Bare domain seed (example.com); cannot be combined with keywords or --url")
            p.add_argument("--limit", type=positive_int, default=200)
        if name == "locations":
            p.add_argument("--name", action="append", required=True)
            p.add_argument("--country-code", help="Two-letter ISO country code to narrow suggestions")
            p.add_argument("--locale", default="en")
        if name == "doctor":
            p.add_argument("--check-planning", action="store_true", help="Also request metrics for supplied keywords and market")
    return root


def prepare(args):
    if args.command == "forecast":
        try:
            args.plan = validate_forecast_plan(json.loads(args.plan_file.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            raise UserError("Invalid forecast plan. Check the documented fields, dates, money, and match types.") from None
    keywords = list(getattr(args, "keyword", []))
    if getattr(args, "keywords_file", None):
        try:
            keywords += args.keywords_file.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError):
            raise UserError("Cannot read keyword file as UTF-8.") from None
    # Preserve spelling while removing exact duplicates and empty lines.
    args.keywords = list(dict.fromkeys(k.strip() for k in keywords if k.strip()))
    if len(getattr(args, "geo_id", None) or []) > 10:
        raise UserError("At most 10 geo-target IDs are supported per request.")
    if args.command in ("ideas", "metrics", "doctor"):
        start, end = args.from_month, args.to_month
        if (start is None) != (end is None):
            raise UserError("Use --from-month and --to-month together.")
        if start and start > end:
            raise UserError("--from-month must not be after --to-month.")
        today = date.today()
        if end and end >= (today.year, today.month):
            raise UserError("--to-month must be before the current month.")
    if args.command == "ideas":
        if args.site:
            if args.keywords or args.url:
                raise UserError("--site cannot be combined with keywords or --url; run a separate ideas request.")
            try:
                site = args.site.encode("idna").decode("ascii").lower()
            except UnicodeError:
                site = ""
            if not re.fullmatch(r"(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}", site):
                raise UserError("--site must be a bare domain such as example.com, without scheme, path, port, or credentials.")
            args.site = site
        elif not args.keywords and not args.url:
            raise UserError("ideas requires --keyword, --keywords-file, --url, or --site.")
        if len(args.keywords) > 20:
            raise UserError("ideas accepts at most 20 seed keywords; narrow seeds or run separate themes.")
        if args.url:
            try:
                url = urlsplit(args.url)
                valid = url.scheme in {"http", "https"} and url.hostname and not url.username and not url.password
            except ValueError:
                valid = False
            if not valid:
                raise UserError("URL must be HTTP(S), with a host and without embedded credentials.")
    if args.command == "metrics" and not args.keywords:
        raise UserError("metrics requires at least one keyword.")
    if args.command == "doctor":
        has_market = bool(args.geo_id or args.worldwide) and bool(args.language_id)
        if args.check_planning and (not args.keywords or not has_market):
            raise UserError("--check-planning requires keywords, a geography (or --worldwide), and --language-id.")
        if not args.check_planning and (args.keywords or args.geo_id or args.worldwide or args.language_id or args.from_month):
            raise UserError("Add --check-planning to use doctor keyword or market arguments.")
    if args.command == "locations" and args.country_code:
        if not re.fullmatch(r"[A-Za-z]{2}", args.country_code):
            raise UserError("--country-code must be a two-letter ISO country code.")
        args.country_code = args.country_code.upper()
    outputs = [p.resolve() for p in (args.output, getattr(args, "csv", None)) if p]
    if len(outputs) != len(set(outputs)):
        raise UserError("JSON and CSV output paths must differ.")
    inputs = [p.resolve() for p in (args.config, getattr(args, "keywords_file", None), getattr(args, "plan_file", None)) if p]
    if any(p in inputs for p in outputs):
        raise UserError("Output paths must not overwrite configuration or keyword inputs.")
    for path in outputs:
        if not path.parent.is_dir() or path.is_dir():
            raise UserError("Output paths must name files in existing directories.")


def money_micros(value):
    """Reject rounding, non-finite values, and invalid protobuf int64 money."""
    try:
        amount = Decimal(str(value)) * 1_000_000
        if not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value() or amount >= 2**63:
            raise ValueError()
        return int(amount)
    except (ValueError, ArithmeticError):
        raise UserError("Money must be positive, finite, and have at most six decimal places.") from None


def validate_forecast_plan(plan):
    allowed = {"currency_code", "geo_ids", "worldwide", "language_id", "start_date", "end_date", "daily_budget", "max_cpc", "bidding_strategy", "ad_groups"}
    if not isinstance(plan, dict) or set(plan) - allowed:
        raise UserError("Unknown forecast fields. v25 cannot model negatives or network selection; retain them in the launch brief.")
    if not re.fullmatch(r"[A-Z]{3}", plan.get("currency_code", "")):
        raise UserError("Forecast currency_code must be a three-letter account currency.")
    geo = plan.get("geo_ids", [])
    worldwide = plan.get("worldwide", False)
    if not isinstance(worldwide, bool) or not isinstance(geo, list) or len(geo) > 10 or len(geo) != len(set(geo)) or bool(geo) == worldwide:
        raise UserError("Specify unique geo_ids (up to 10) or explicit worldwide: true.")
    for value in [*geo, plan.get("language_id", "")]:
        if not isinstance(value, str) or not re.fullmatch(r"[1-9]\d*", value):
            raise UserError("Location and language IDs must be positive numeric strings.")
    start, end = date.fromisoformat(plan["start_date"]), date.fromisoformat(plan["end_date"])
    if end < start:
        raise UserError("Forecast end_date must be on or after start_date.")
    money_micros(plan["daily_budget"])
    money_micros(plan["max_cpc"])
    if plan.get("bidding_strategy") not in {"manual_cpc", "maximize_clicks"}:
        raise UserError("Choose manual_cpc or maximize_clicks for click forecasts.")
    groups = plan.get("ad_groups")
    if not isinstance(groups, list) or not groups:
        raise UserError("At least one nonempty ad group is required.")
    names = set()
    for group in groups:
        if set(group) != {"id", "keywords"} or not isinstance(group["id"], str) or not group["id"] or group["id"] in names:
            raise UserError("Each ad group needs a unique id and keywords.")
        names.add(group["id"])
        if not isinstance(group["keywords"], list) or not group["keywords"]:
            raise UserError("Each ad group needs keywords.")
        seen = set()
        for keyword in group["keywords"]:
            if set(keyword) != {"text", "match_type"} or not isinstance(keyword["text"], str) or not keyword["text"].strip() or keyword["match_type"] not in {"EXACT", "PHRASE"}:
                raise UserError("Forecast keywords need text and EXACT or PHRASE match_type.")
            key = (keyword["text"].strip().casefold(), keyword["match_type"])
            if key in seen:
                raise UserError("Remove duplicate keywords within each ad group.")
            seen.add(key)
    return plan


def forecast(client, calls, args, account_data):
    plan = args.plan
    if plan["currency_code"] != account_data["currency_code"]:
        raise UserError("Forecast and account currencies differ; use account currency throughout the viability plan.")
    rows = search(client, calls, args.customer_id, "SELECT customer.time_zone FROM customer LIMIT 1")
    if not rows or not rows[0].customer.time_zone:
        raise UserError("Cannot establish the account timezone for forecast dates.")
    account_zone = rows[0].customer.time_zone
    today = datetime.now(ZoneInfo(account_zone)).date()
    start, end = date.fromisoformat(plan["start_date"]), date.fromisoformat(plan["end_date"])
    # Use a calendar year, including leap-day handling.
    try:
        latest = today.replace(year=today.year + 1)
    except ValueError:
        latest = today.replace(year=today.year + 1, day=28)
    if start <= today or end > latest:
        raise UserError("Forecast must start in the future and end within one year in the account timezone.")
    request = client.get_type("GenerateKeywordForecastMetricsRequest")
    request.customer_id = args.customer_id
    request.forecast_period.start_date, request.forecast_period.end_date = plan["start_date"], plan["end_date"]
    campaign = request.campaign
    campaign.geo_target_constants.extend(f"geoTargetConstants/{v}" for v in plan.get("geo_ids", []))
    campaign.language_constants.append(f"languageConstants/{plan['language_id']}")
    strategy = campaign.bidding_strategy
    if plan["bidding_strategy"] == "manual_cpc":
        strategy.manual_cpc_bidding_strategy.daily_budget_micros = money_micros(plan["daily_budget"])
        strategy.manual_cpc_bidding_strategy.max_cpc_bid_micros = money_micros(plan["max_cpc"])
    else:
        strategy.maximize_clicks_bidding_strategy.daily_target_spend_micros = money_micros(plan["daily_budget"])
        strategy.maximize_clicks_bidding_strategy.max_cpc_bid_ceiling_micros = money_micros(plan["max_cpc"])
    for group in plan["ad_groups"]:
        ad_group = client.get_type("ForecastAdGroup")
        for keyword in group["keywords"]:
            item = client.get_type("KeywordInfo")
            item.text = keyword["text"]
            item.match_type = getattr(client.enums.KeywordMatchTypeEnum, keyword["match_type"])
            ad_group.keywords.append(item)
        campaign.ad_groups.append(ad_group)
    service = client.get_service("KeywordPlanIdeaService")
    response = calls.run(lambda: service.generate_keyword_forecast_metrics(request=request, retry=None, timeout=30), planning=True)
    metrics = response.campaign_forecast_metrics
    values = {name: field(metrics, name) for name in ("clicks", "cost_micros", "average_cpc_micros")}
    days = (end - start).days + 1
    for source, target in (("cost_micros", "cost"), ("average_cpc_micros", "average_cpc")):
        values[target] = currency(values[source])
    values["daily_clicks"] = str(Decimal(str(values["clicks"])) / days) if values["clicks"] is not None else None
    values["daily_cost"] = str(Decimal(values["cost"]) / days) if values["cost"] is not None else None
    return {"request": plan, "account_timezone": account_zone, "period_days": days, "metrics_basis": "period_total", "results": values,
            "warnings": ["v25 forecasts do not accept negatives or network selection; these launch settings are not modeled.",
                         "Campaign totals only. Separate profile scenarios are not additive campaign estimates.",
                         "Forecasts are estimates; conversions must be calculated from explicit funnel assumptions."]}


def load_client(args):
    from google.ads.googleads import config
    from google.ads.googleads.client import GoogleAdsClient

    # Do not enable request/response logging through user YAML configuration.
    # The SDK's interceptor otherwise logs raw server failure messages at WARNING.
    logging.getLogger("google.ads.googleads.client").disabled = True
    try:
        if args.config:
            settings = config.load_from_yaml_file(str(args.config))
        else:
            if os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH"):
                raise UserError("Use --config for YAML configuration, or unset GOOGLE_ADS_CONFIGURATION_FILE_PATH to use environment credentials.")
            settings = config.load_from_env()
        settings.pop("logging", None)
        client = GoogleAdsClient.load_from_dict(settings, version=API_VERSION)
        if not client.use_proto_plus:
            raise UserError("Set use_proto_plus: true in YAML or GOOGLE_ADS_USE_PROTO_PLUS=true.")
        return client
    except UserError:
        raise
    except Exception as exc:
        raise UserError(f"Cannot load Google Ads configuration ({type(exc).__name__}). Set OAuth client ID, client secret, refresh token, and use_proto_plus=true; see references/setup.md.") from None


def search(client, calls, cid, query):
    service = client.get_service("GoogleAdsService")
    return calls.run(lambda: [row for batch in service.search_stream(customer_id=cid, query=query, retry=None, timeout=30) for row in batch.results])


def account(client, calls, cid):
    rows = search(client, calls, cid, "SELECT customer.id, customer.currency_code, customer.test_account FROM customer LIMIT 1")
    if not rows:
        raise UserError("No customer returned. Check the target customer ID and account permissions.")
    c = rows[0].customer
    return {"customer_id": str(c.id), "currency_code": c.currency_code, "test_account": c.test_account}


def field(message, name):
    return getattr(message, name) if message._pb.HasField(name) else None


def currency(micros):
    """Convert micros to an exact decimal string in account currency."""
    return str(Decimal(micros) / Decimal(1_000_000)) if micros is not None else None


def concept(item):
    kind = item.concept_group.type_.name
    return {"name": item.name, "group": item.concept_group.name, "group_type": None if kind in ("UNSPECIFIED", "UNKNOWN") else kind}


def normalize(result, metric_field):
    metrics = getattr(result, metric_field)
    row = {"keyword": result.text, "close_variants": list(getattr(result, "close_variants", []))}
    for name in ("avg_monthly_searches", "competition_index", "low_top_of_page_bid_micros", "high_top_of_page_bid_micros", "average_cpc_micros"):
        row[name] = field(metrics, name)
    row["competition"] = metrics.competition.name if metrics.competition else None
    if row["competition"] == "UNKNOWN":
        row["competition"] = None
    for name in ("low_top_of_page_bid", "high_top_of_page_bid", "average_cpc"):
        row[name] = currency(row[f"{name}_micros"])
    row["monthly_search_volumes"] = sorted(
        [{"month": f"{m.year:04d}-{int(m.month) - 1:02d}", "searches": field(m, "monthly_searches")} for m in metrics.monthly_search_volumes],
        key=lambda item: item["month"],
    )
    # Only GenerateKeywordIdeas returns annotations; historical rows carry no concepts key.
    if metric_field == "keyword_idea_metrics":
        row["concepts"] = [concept(c) for c in result.keyword_annotations.concepts]
    return row


def targeting(client, request, args):
    request.customer_id = args.customer_id
    request.language = f"languageConstants/{args.language_id}"
    request.geo_target_constants.extend(f"geoTargetConstants/{v}" for v in (args.geo_id or []))
    network = client.enums.KeywordPlanNetworkEnum
    request.keyword_plan_network = network.GOOGLE_SEARCH if args.network == "google" else network.GOOGLE_SEARCH_AND_PARTNERS
    options = request.historical_metrics_options
    options.include_average_cpc = True
    if args.from_month:
        for target, (year, month) in ((options.year_month_range.start, args.from_month), (options.year_month_range.end, args.to_month)):
            target.year = year
            target.month = client.enums.MonthOfYearEnum(month + 1)  # JANUARY is enum value 2


def ideas(client, calls, args):
    request = client.get_type("GenerateKeywordIdeasRequest")
    targeting(client, request, args)
    request.keyword_annotation.append(client.enums.KeywordPlanKeywordAnnotationEnum.KEYWORD_CONCEPT)
    if args.site:
        request.site_seed.site = args.site
    elif args.url and args.keywords:
        request.keyword_and_url_seed.url = args.url
        request.keyword_and_url_seed.keywords.extend(args.keywords)
    elif args.url:
        request.url_seed.url = args.url
    else:
        request.keyword_seed.keywords.extend(args.keywords)
    service = client.get_service("KeywordPlanIdeaService")
    rows, total = [], None
    # Keep page_size constant: the API expects it unchanged across page tokens.
    request.page_size = min(1000, args.limit + 1)
    while True:
        # Consume only the first page; advance tokens ourselves to pace and retry each RPC.
        pager = calls.run(lambda: service.generate_keyword_ideas(request=request, retry=None, timeout=30), planning=True)
        page = next(iter(pager.pages))
        if not request.page_token:
            total = page.total_size or None
        rows.extend(normalize(result, "keyword_idea_metrics") for result in page.results)
        if len(rows) >= args.limit:
            return rows[:args.limit], bool(len(rows) > args.limit or page.next_page_token), total
        if not page.next_page_token:
            return rows, False, total
        request.page_token = page.next_page_token


def metrics(client, calls, args):
    service = client.get_service("KeywordPlanIdeaService")
    rows = []
    for offset in range(0, len(args.keywords), 10_000):
        request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
        targeting(client, request, args)
        request.keywords.extend(args.keywords[offset:offset + 10_000])
        response = calls.run(lambda: service.generate_keyword_historical_metrics(request=request, retry=None, timeout=30), planning=True)
        rows.extend(normalize(result, "keyword_metrics") for result in response.results)
    # Keep API grouping intact, including any overlap between independently batched requests.
    matched = {text.casefold() for r in rows for text in [r["keyword"], *r["close_variants"]]}
    return rows, [k for k in args.keywords if k.casefold() not in matched]


def execute(client, calls, args):
    data = {"command": args.command, "retrieved_at": datetime.now(timezone.utc).isoformat(), "api_version": API_VERSION}
    if args.command == "locations":
        request = client.get_type("SuggestGeoTargetConstantsRequest")
        request.locale = args.locale
        if args.country_code:
            request.country_code = args.country_code
        request.location_names.names.extend(args.name)
        service = client.get_service("GeoTargetConstantService")
        response = calls.run(lambda: service.suggest_geo_target_constants(request=request, retry=None, timeout=30))
        data["results"] = [{"id": str(s.geo_target_constant.id), "name": s.geo_target_constant.name, "canonical_name": s.geo_target_constant.canonical_name, "country_code": s.geo_target_constant.country_code, "target_type": s.geo_target_constant.target_type, "status": s.geo_target_constant.status.name} for s in response.geo_target_constant_suggestions]
        return data
    if args.command == "languages":
        rows = search(client, calls, args.customer_id, "SELECT language_constant.id, language_constant.code, language_constant.name, language_constant.targetable FROM language_constant")
        data["results"] = [{"id": str(r.language_constant.id), "code": r.language_constant.code, "name": r.language_constant.name, "targetable": r.language_constant.targetable} for r in rows]
        return data
    data["account"] = account(client, calls, args.customer_id)
    if args.command == "forecast":
        if data["account"]["test_account"]:
            raise UserError("Forecasts require a production Google Ads customer.")
        data.update(forecast(client, calls, args, data["account"]))
        return data
    if args.command == "doctor" and not args.check_planning:
        data.update(account_access="verified", planning_access="not_checked")
        return data
    period = "API default: previous 12 months"
    if args.from_month:
        period = "{:04d}-{:02d} to {:04d}-{:02d}".format(*args.from_month, *args.to_month)
    data["request"] = {"keywords": args.keywords, "url": getattr(args, "url", None), "site": getattr(args, "site", None), "geo_ids": args.geo_id or [], "worldwide": args.worldwide, "language_id": args.language_id, "network": args.network, "period": period}
    data["warnings"] = ["Approximate demand; advertising competition is not organic ranking difficulty."]
    if data["account"]["test_account"]:
        raise UserError("Keyword research requires a production Google Ads customer; this is a test account.")
    if args.command == "ideas":
        data["results"], data["truncated"], data["total_available"] = ideas(client, calls, args)
        data["request"]["limit"] = args.limit
    else:
        data["results"], data["unmatched_keywords"] = metrics(client, calls, args)
        data["truncated"] = False
        if len(args.keywords) > 10_000:
            data["warnings"].append("Separate historical batches may contain overlapping close variants; do not sum their volumes.")
    data["returned_months"] = sorted({m["month"] for r in data["results"] for m in r["monthly_search_volumes"]})
    if args.command == "doctor":
        data.update(account_access="verified", planning_access="verified")
    return data


def csv_text(data):
    if data["command"] == "forecast":
        row = {"currency_code": data["account"]["currency_code"], "retrieved_at": data["retrieved_at"],
               "start_date": data["request"]["start_date"], "end_date": data["request"]["end_date"],
               "period_days": data["period_days"], "metrics_basis": data["metrics_basis"], **data["results"],
               "warnings": " ".join(data["warnings"])}
        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
        return out.getvalue()
    columns = ["keyword", "close_variants", "avg_monthly_searches", "competition", "competition_index", "low_top_of_page_bid_micros", "high_top_of_page_bid_micros", "low_top_of_page_bid", "high_top_of_page_bid", "average_cpc_micros", "average_cpc", "concepts", "currency_code", "geo_ids", "worldwide", "language_id", "network", "retrieved_at", "truncated"]
    months = data["returned_months"]
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns + months)
    writer.writeheader()
    for result in data["results"]:
        row = {k: result.get(k) for k in columns}
        row.update({k: data["request"][k] for k in ("worldwide", "language_id", "network")})
        row.update(currency_code=data["account"]["currency_code"], geo_ids=";".join(data["request"]["geo_ids"]), close_variants=";".join(result["close_variants"]), retrieved_at=data["retrieved_at"], truncated=data["truncated"])
        row["concepts"] = ";".join(f"{c['group_type']}:{c['name']}" if c["group_type"] else c["name"] for c in result.get("concepts") or [])
        row.update({m["month"]: m["searches"] for m in result["monthly_search_volumes"]})
        writer.writerow({k: escape_formula(v) for k, v in row.items()})
    return out.getvalue()


def escape_formula(value):
    """Prevent spreadsheet formula execution for untrusted keyword/URL-derived strings."""
    if isinstance(value, str) and (value.startswith(("\t", "\r")) or value.lstrip().startswith(("=", "+", "-", "@"))):
        return "'" + value
    return value


def cell(value):
    if isinstance(value, bool):
        return str(value).lower()
    return "" if value is None else re.sub(r"\s*[\t\r\n]+\s*", " ", str(value))


def summary(data, outputs):
    """Compact TSV for stdout when full JSON goes to a file."""
    request = data.get("request") or {}
    results = data.get("results")
    meta = {"command": data["command"]}
    if "language_id" in request:
        meta["market"] = "worldwide" if request.get("worldwide") else ",".join(request.get("geo_ids", []))
        meta["language"] = request["language_id"]
    for key in ("network", "period", "start_date", "end_date"):
        if key in request:
            meta[key] = request[key]
    if isinstance(results, list):
        meta["rows"] = len(results)
    for key in ("truncated", "total_available", "account_timezone", "account_access", "planning_access"):
        if key in data:
            meta[key] = data[key]
    if "unmatched_keywords" in data:
        meta["unmatched"] = len(data["unmatched_keywords"])
    meta["outputs"] = ",".join(str(p) for p in outputs)
    lines = ["\t".join(f"{k}={cell(v)}" for k, v in meta.items())]
    if data["command"] == "forecast":
        columns = ["clicks", "cost", "average_cpc", "daily_clicks", "daily_cost"]
        rows = [results]
    elif data["command"] == "locations":
        columns, rows = ["id", "canonical_name", "target_type", "status"], results
    elif data["command"] == "languages":
        columns, rows = ["id", "code", "name", "targetable"], results
    elif isinstance(results, list):
        columns = ["keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid", "average_cpc", "brand_concepts"]
        rows = [{**r, "brand_concepts": ";".join(f"{c['group_type']}:{c['name']}" for c in r.get("concepts", []) if c["group_type"] in ("BRAND", "OTHER_BRANDS"))} for r in results]
    else:
        return lines[0] + "\n"
    lines.append("\t".join(columns))
    lines.extend("\t".join(cell(row.get(c)) for c in columns) for row in rows)
    return "\n".join(lines) + "\n"


def atomic_write(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            f.write(content)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        prepare(args)
        data = execute(load_client(args), Calls(), args)
        rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        spreadsheet = csv_text(data) if getattr(args, "csv", None) else None
        if spreadsheet is not None:
            atomic_write(args.csv, spreadsheet)
        if args.output:
            atomic_write(args.output, rendered)
            print(summary(data, [p for p in (args.output, getattr(args, "csv", None)) if p]), end="")
        else:
            print(rendered, end="")
        return 0
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"error: {type(exc).__name__}; no successful result emitted. Check output permissions and SDK compatibility.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
