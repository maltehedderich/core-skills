#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyjwt[crypto]>=2.10,<3"]
# ///
"""Read-only Apple Ads campaign reporting and App Store keyword research. Run with: uv run apple_ads.py --help."""

import argparse
import csv
import io
import json
import os
import random
import re
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

API_VERSION = "v1"
API_BASE = "https://api.ads.apple.com/v1"
TOKEN_URL = "https://appleid.apple.com/auth/oauth2/token"
CONFIG_KEYS = ("client_id", "team_id", "key_id", "private_key_path")
COMMANDS = ("doctor", "apps", "app", "campaigns", "report", "ideas", "phrases", "popularity", "impression-share")
LIMITS = {"apps": 50, "campaigns": 1000, "report": 1000, "ideas": 200, "phrases": 200, "popularity": 1000, "impression-share": 1000}
GENRES = ("BUSINESS", "EDUCATION", "ENTERTAINMENT", "FINANCE", "FOOD_DRINK", "GAMES", "HEALTH_FITNESS", "LIFESTYLE", "NEW_PUBLICATION",
          "PHOTO_VIDEO", "PRODUCTIVITY_UTILITIES", "SHOPPING", "SOCIAL_NETWORKING", "SPORTS", "TRAVEL")
ENTITY_DIMENSIONS = ("deviceClass", "ageRange", "gender", "countryCode", "adminArea", "locality", "countryOrRegion")
GROUP_BY = {"campaigns": ENTITY_DIMENSIONS, "adgroups": ENTITY_DIMENSIONS, "keywords": ("deviceClass", "countryOrRegion"), "searchterms": ("deviceClass", "countryOrRegion")}
SNAKE = {"deviceClass": "device_class", "ageRange": "age_range", "gender": "gender", "countryCode": "country_code",
         "adminArea": "admin_area", "locality": "locality", "countryOrRegion": "country_or_region"}
# Apple metric name -> output key. Money objects become decimal strings in the report currency.
METRICS = {"impressions": "impressions", "taps": "taps", "ttr": "ttr", "localSpend": "local_spend", "cpt": "cpt", "cpm": "cpm",
           "tapInstalls": "tap_installs", "tapInstallCPI": "tap_install_cpi", "tapInstallRate": "tap_install_rate",
           "viewInstalls": "view_installs", "totalInstalls": "total_installs", "totalAvgCPI": "total_avg_cpi", "totalInstallRate": "total_install_rate",
           "tapNewDownloads": "tap_new_downloads", "tapRedownloads": "tap_redownloads", "viewNewDownloads": "view_new_downloads",
           "viewRedownloads": "view_redownloads", "totalNewDownloads": "total_new_downloads", "totalRedownloads": "total_redownloads",
           "tapPreOrdersPlaced": "tap_pre_orders_placed", "viewPreOrdersPlaced": "view_pre_orders_placed", "totalPreOrdersPlaced": "total_pre_orders_placed"}
POPULARITY_FIELDS = ["rankInGenre", "searchPopularityInGenre", "searchPopularity1to100", "searchPopularity1to5"]


class UserError(Exception):
    """An actionable error safe to show without credential or token contents."""


def clean(value, length=160):
    """Treat server text as untrusted: strip control characters and bound its length."""
    text = re.sub(r"[\x00-\x1f\x7f\s]+", " ", str(value)).strip()
    return text[:length] + ("..." if len(text) > length else "")


def api_error(status, data):
    """Summarize Apple's error envelope: codes, fields, and short messages, never request headers."""
    error = data.get("error") if isinstance(data, dict) else None
    parts = []
    if isinstance(error, dict):
        head = clean(error.get("code") or "UNKNOWN", 60)
        if error.get("message"):
            head += f": {clean(error['message'])}"
        parts.append(head)
        for detail in (error.get("details") or [])[:5]:
            if not isinstance(detail, dict):
                continue
            text = clean(detail.get("code") or "DETAIL", 60)
            info = detail.get("info") if isinstance(detail.get("info"), dict) else {}
            if info.get("field"):
                text += f" on {clean(info['field'], 60)}"
            if detail.get("message"):
                text += f": {clean(detail['message'])}"
            parts.append(text)
    hint = {401: " Check credentials and the searchadsorg scope.", 403: " Check the API user's role on this ad account.",
            404: " Check the IDs and --ad-account-id.", 429: " Rate limit persisted after retries; retry later and run one process per ad account."}.get(status, "")
    return f"Apple Ads API error (HTTP {status}): {'; '.join(parts) or 'no error details'}.{hint} See references/setup.md."


class Credentials:
    def __init__(self, client_id, team_id, key_id, key, key_path):
        self.client_id, self.team_id, self.key_id, self.key, self.key_path = client_id, team_id, key_id, key, key_path


def load_credentials(args):
    from cryptography.exceptions import UnsupportedAlgorithm
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    if args.config:
        try:
            with args.config.open("rb") as f:
                settings = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            raise UserError("Cannot read --config as TOML; see references/setup.md.") from None
        unknown = sorted(set(settings) - set(CONFIG_KEYS))
        if unknown:
            raise UserError(f"Unknown configuration keys: {', '.join(unknown)}. Use {', '.join(CONFIG_KEYS)}.")
    else:
        settings = {key: os.environ.get("APPLE_ADS_" + key.upper()) for key in CONFIG_KEYS}
    missing = [key for key in CONFIG_KEYS if not isinstance(settings.get(key), str) or not settings[key].strip()]
    if missing:
        raise UserError(f"Missing Apple Ads credentials: {', '.join(missing)}. Use --config TOML or APPLE_ADS_* environment variables; see references/setup.md.")
    path = Path(settings["private_key_path"].strip()).expanduser()
    if args.config and not path.is_absolute():
        path = args.config.parent / path
    try:
        key = load_pem_private_key(path.read_bytes(), password=None)
    except OSError:
        raise UserError("Cannot read the file named by private_key_path.") from None
    except (ValueError, TypeError, UnsupportedAlgorithm):
        raise UserError("private_key_path must name an unencrypted PEM EC private key; see references/setup.md.") from None
    if not isinstance(key, ec.EllipticCurvePrivateKey) or key.curve.name != "secp256r1":
        raise UserError("The private key must use the prime256v1 (P-256) curve that Apple Ads requires.")
    return Credentials(*(settings[k].strip() for k in CONFIG_KEYS[:3]), key, path.resolve())


def client_secret(credentials, now=None):
    """Sign a short-lived ES256 client secret. Apple allows up to 180 days; one run needs minutes."""
    import jwt

    issued = int(time.time() if now is None else now)
    claims = {"sub": credentials.client_id, "iss": credentials.team_id, "aud": "https://appleid.apple.com", "iat": issued, "exp": issued + 600}
    return jwt.encode(claims, credentials.key, algorithm="ES256", headers={"kid": credentials.key_id})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward the bearer token to a redirected host."""

    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def urllib_transport(method, url, headers, body):
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with OPENER.open(request, timeout=30) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in (exc.headers or {}).items()}, exc.read()


def seconds(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number < float("inf") else None


def parse(payload):
    try:
        return json.loads(payload)
    except (TypeError, ValueError):
        return None


class Client:
    """Read-only Apple Ads client: OAuth token, ad account context, rate-limit pacing, and retries."""

    def __init__(self, credentials, transport=None, sleep=time.sleep):
        self.credentials, self.sleep = credentials, sleep
        self.transport = transport or urllib_transport
        self.token = None

    def send(self, method, url, headers, body):
        wait = 2
        for attempt in range(4):
            try:
                status, response_headers, payload = self.transport(method, url, headers, body)
            except OSError:
                status, response_headers, payload = None, {}, b""
            if status is not None and status != 429 and status < 500:
                self.pace(response_headers)
                return status, payload
            if attempt == 3:
                if status is None:
                    raise UserError("Cannot reach Apple after retries; check network access and retry later.")
                return status, payload
            # Apple: prefer Retry-After on 429, then RateLimit-Reset; otherwise double the wait up to 16 seconds.
            delay = seconds(response_headers.get("retry-after")) if status == 429 else None
            if delay is None and status == 429:
                delay = seconds(response_headers.get("ratelimit-reset"))
            self.sleep(min(60, delay) if delay is not None else wait + random.uniform(0, 0.25))
            wait = min(wait * 2, 16)

    def pace(self, headers):
        remaining, reset = seconds(headers.get("ratelimit-remaining")), seconds(headers.get("ratelimit-reset"))
        if remaining is not None and reset is not None and remaining < 5:
            self.sleep(min(60, reset))

    def authenticate(self):
        form = {"grant_type": "client_credentials", "client_id": self.credentials.client_id,
                "client_secret": client_secret(self.credentials), "scope": "searchadsorg"}
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
        status, payload = self.send("POST", TOKEN_URL, headers, urllib.parse.urlencode(form).encode())
        data = parse(payload)
        token = data.get("access_token") if isinstance(data, dict) else None
        if status != 200 or not isinstance(token, str) or not token:
            code = data.get("error") if isinstance(data, dict) and isinstance(data.get("error"), str) else "no error code"
            raise UserError(f"Apple OAuth token request failed (HTTP {status}, {clean(code, 40)}). Check client_id, team_id, key_id, "
                            "the uploaded public key, and the system clock; see references/setup.md.")
        self.token = token

    def call(self, method, path, account_id=None, body=None, query=None):
        # Read-only by construction: only GET and POST .../query requests are ever sent.
        if method not in ("GET", "POST") or (method == "POST" and not path.endswith("/query")):
            raise UserError("Refusing a request that could change Apple Ads data.")
        url = API_BASE + path + ("?" + urllib.parse.urlencode(query, doseq=True) if query else "")
        data = json.dumps(body).encode() if body is not None else None
        for refresh in (True, False):
            if self.token is None:
                self.authenticate()
            headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
            if account_id:
                headers["X-AP-Context"] = f"adAccountId={account_id}"
            if data is not None:
                headers["Content-Type"] = "application/json"
            status, payload = self.send(method, url, headers, data)
            if status == 401 and refresh:
                self.token = None  # Expired or revoked mid-run; request one fresh token.
                continue
            break
        result = parse(payload)
        if status != 200 or not isinstance(result, dict) or result.get("error"):
            raise UserError(api_error(status, result))
        return result


def numeric_id(value):
    if not re.fullmatch(r"[1-9]\d{0,19}", value):
        raise argparse.ArgumentTypeError("use a positive numeric ID")
    return value


def country(value):
    if not re.fullmatch(r"[A-Za-z]{2}", value):
        raise argparse.ArgumentTypeError("use a two-letter ISO country or region code")
    return value.upper()


def iso_date(value):
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("use YYYY-MM-DD")


def sort_spec(value):
    match = re.fullmatch(r"([A-Za-z][A-Za-z0-9]*):(asc|desc)", value, re.IGNORECASE)
    if not match:
        raise argparse.ArgumentTypeError("use FIELD:asc or FIELD:desc with Apple's field name, e.g. localSpend:desc")
    return {"field": match[1], "order": match[2].upper()}


def positive_int(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return result


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        p = sub.add_parser(name)
        p.add_argument("--ad-account-id", type=numeric_id, required=name != "doctor", help="Ad account ID listed by doctor; sent as X-AP-Context")
        p.add_argument("--config", type=Path, help="External Apple Ads TOML; otherwise use APPLE_ADS_* environment variables")
        p.add_argument("--output", type=Path, help="JSON file; defaults to stdout")
        if name in LIMITS:
            p.add_argument("--csv", type=Path, help="Optional spreadsheet export")
            p.add_argument("--limit", type=positive_int, default=LIMITS[name], help="Maximum rows to return")
        if name in ("app", "ideas"):
            p.add_argument("--adam-id", type=numeric_id, required=True, help="App Store app ID (Adam ID)")
        if name in ("campaigns", "phrases"):
            p.add_argument("--adam-id", type=numeric_id, help="App Store app ID (Adam ID)")
        if name == "impression-share":
            p.add_argument("--adam-id", type=numeric_id, action="append", required=True, help="Promoted app ID; repeat for several apps")
        if name in ("ideas", "phrases", "popularity", "impression-share"):
            p.add_argument("--term", action="append", default=[])
            p.add_argument("--terms-file", type=Path, help="UTF-8, one term per line")
        if name in ("ideas", "impression-share"):
            p.add_argument("--country", type=country, action="append", help="App Store country or region code; repeat for several")
        if name in ("report", "popularity", "impression-share"):
            p.add_argument("--start", type=iso_date, required=True, help="First day, YYYY-MM-DD (inclusive)")
            p.add_argument("--end", type=iso_date, required=True, help="Last day, YYYY-MM-DD (inclusive)")
            p.add_argument("--sort", type=sort_spec, action="append", help="Apple field and direction, e.g. localSpend:desc")
        if name in ("popularity", "impression-share"):
            p.add_argument("--contains", help="Match search terms containing this text (case-insensitive)")
        if name == "apps":
            p.add_argument("--query", help="App or developer name, at least 3 characters")
            p.add_argument("--owned", action="store_true", help="Return apps owned by your organization")
            p.add_argument("--storefront", type=country, action="append", help="Limit to an App Store country or region; repeatable")
        if name == "campaigns":
            p.add_argument("--status", choices=("ENABLED", "PAUSED"))
        if name == "report":
            p.add_argument("--level", choices=tuple(GROUP_BY), required=True)
            p.add_argument("--campaign-id", type=numeric_id, action="append", help="Required (once) below campaign level; repeatable for campaigns")
            p.add_argument("--ad-group-id", type=numeric_id)
            p.add_argument("--granularity", choices=("hourly", "daily", "weekly", "monthly"), help="Omit for period totals only")
            p.add_argument("--time-zone", choices=("ortz", "utc"), default="ortz", help="ortz is the account's time zone")
            p.add_argument("--group-by", choices=ENTITY_DIMENSIONS, action="append")
            p.add_argument("--include-empty", action="store_true", help="Also return entities without activity; not with --group-by")
        if name == "phrases":
            p.add_argument("--like", help="Partial phrase match (SEARCH route)")
        if name == "popularity":
            p.add_argument("--country", type=country, action="append", required=True, help="App Store country or region code; repeat for several")
            p.add_argument("--genre", choices=GENRES, action="append", help="App Store genre; repeat for several; omit for all genres")
            p.add_argument("--granularity", choices=("weekly", "monthly"), required=True)
        if name == "impression-share":
            p.add_argument("--granularity", choices=("daily", "weekly"), required=True)
            p.add_argument("--slot", choices=("first", "all"), default="first", help="first: top ad position only; all: any ad position")
    return root


def prepare(args):
    terms = list(getattr(args, "term", None) or [])
    if getattr(args, "terms_file", None):
        try:
            terms += args.terms_file.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError):
            raise UserError("Cannot read terms file as UTF-8.") from None
    # Preserve spelling while removing exact duplicates and empty lines.
    args.terms = list(dict.fromkeys(t.strip() for t in terms if t.strip()))
    for name in ("country", "storefront", "campaign_id", "adam_id", "genre", "group_by"):
        if isinstance(getattr(args, name, None), list):
            setattr(args, name, list(dict.fromkeys(getattr(args, name))))
    if getattr(args, "start", None) and args.start > args.end:
        raise UserError("--start must not be after --end.")
    if args.command == "apps" and not (args.query or args.owned):
        raise UserError("apps requires --query, --owned, or both.")
    if args.command == "report":
        validate_report(args)
    if args.command == "phrases" and sum(map(bool, (args.adam_id, args.terms, args.like))) != 1:
        raise UserError("phrases takes exactly one of --adam-id (discover), --term/--terms-file (exact lookup), or --like (partial match).")
    if args.command in ("popularity", "impression-share"):
        if args.terms and args.contains:
            raise UserError("Use --term/--terms-file or --contains, not both.")
        if len(args.sort or []) > 2:
            raise UserError("Insights queries accept at most two --sort fields.")
    if args.command == "impression-share":
        days = (args.end - args.start).days + 1
        if args.granularity == "daily" and days > 30:
            raise UserError("Daily impression share covers at most 30 days.")
        if args.granularity == "weekly" and (args.start.weekday() != 6 or days > 28):
            raise UserError("Weekly impression share must start on a Sunday and cover at most 4 weeks.")
    outputs = [p.resolve() for p in (args.output, getattr(args, "csv", None)) if p]
    if len(outputs) != len(set(outputs)):
        raise UserError("JSON and CSV output paths must differ.")
    inputs = [p.resolve() for p in (args.config, getattr(args, "terms_file", None)) if p]
    if any(p in inputs for p in outputs):
        raise UserError("Output paths must not overwrite configuration or terms inputs.")
    for path in outputs:
        if not path.parent.is_dir() or path.is_dir():
            raise UserError("Output paths must name files in existing directories.")


def validate_report(args):
    level, days = args.level, (args.end - args.start).days + 1
    if level != "campaigns" and len(args.campaign_id or []) != 1:
        raise UserError(f"{level} reports need exactly one --campaign-id; run one report per campaign.")
    if args.ad_group_id and level == "campaigns":
        raise UserError("--ad-group-id applies to adgroups, keywords, and searchterms reports.")
    if any(d not in GROUP_BY[level] for d in args.group_by or []):
        raise UserError(f"{level} reports support --group-by {', '.join(GROUP_BY[level])}.")
    if args.include_empty and args.group_by:
        raise UserError("--include-empty cannot be combined with --group-by.")
    if level == "searchterms" and args.time_zone != "ortz":
        raise UserError("Search term reports support only the account time zone (ortz).")
    spans = {"hourly": days <= 7, "daily": days <= 90, "weekly": days >= 14, "monthly": days >= 90}
    if args.granularity and not spans[args.granularity]:
        raise UserError("Inclusive date spans: hourly up to 7 days, daily up to 90, weekly at least 14, monthly at least 90. Omit --granularity for totals.")
    if args.granularity == "hourly":
        if level == "searchterms":
            raise UserError("Hourly granularity is unavailable for search term reports.")
        if args.start < date.today() - timedelta(days=365):
            raise UserError("Hourly reports must start within the last 365 days.")


def flt(field, operator, value):
    return {"field": field, "operator": operator, "value": value}


def one_or_many(field, values):
    return flt(field, "EQUALS", values[0]) if len(values) == 1 else flt(field, "IN", values)


def sid(value):
    return None if value is None else str(value)


def total(response):
    count = (response.get("pagination") or {}).get("totalCount")
    return count if isinstance(count, int) and not isinstance(count, bool) else None


def money(value, currencies):
    """Return Apple's decimal amount string and record its currency. Accepts Money or ReportingMoney."""
    if isinstance(value, dict) and isinstance(value.get("value"), dict):
        value = value["value"]
    if not isinstance(value, dict) or value.get("amount") is None:
        return None
    if value.get("currency"):
        currencies.add(value["currency"])
    return str(value["amount"])


def decimal_text(value):
    if value is None:
        return None
    return format(Decimal(repr(value) if isinstance(value, float) else str(value)), "f")


def metrics(source, currencies):
    """Missing metrics stay null; observed zeros stay zero."""
    return {key: money(source.get(name), currencies) if isinstance(source.get(name), dict) else source.get(name) for name, key in METRICS.items()}


def paged(fetch, limit, max_page):
    """Offset pagination that requests one extra row to detect truncation."""
    rows, offset, available = [], 0, None
    size = min(max_page, limit + 1)
    while True:
        page, available = fetch(offset, size)
        rows.extend(page)
        offset += len(page)
        if len(rows) > limit:
            return rows[:limit], True, available
        # A short page ends the results unless Apple reports more rows (it may clamp the page size).
        if not page or (available is not None and offset >= available) or (available is None and len(page) < size):
            return rows, False, available


def account(client, account_id):
    result = client.call("GET", f"/ad-accounts/{account_id}", account_id).get("result") or {}
    return {"ad_account_id": sid(result.get("id")), "name": result.get("name"), "currency": result.get("currency"),
            "timezone": result.get("timezone"), "system_status": result.get("systemStatus"), "product_features": result.get("productFeatures") or []}


def single_currency(currencies, expected, warnings):
    if len(currencies) > 1 or (expected and currencies and currencies != {expected}):
        warnings.append(f"Mixed currencies returned ({', '.join(sorted(currencies | ({expected} if expected else set())))}); do not add amounts across them.")
    return next(iter(currencies)) if len(currencies) == 1 else expected


def doctor(client, args):
    acls = (client.call("GET", "/acls").get("result") or {}).get("acls") or []
    rows = [{"ad_account_id": sid((a.get("adAccount") or {}).get("id")), "name": (a.get("adAccount") or {}).get("name"),
             "org_id": sid((a.get("adAccount") or {}).get("orgId")), "roles": a.get("roles") or []} for a in acls]
    data = {"token": "verified", "results": rows, "warnings": []}
    if not rows:
        data["warnings"].append("The token can access no ad accounts; ask an account administrator to assign an API role.")
    if args.ad_account_id:
        if args.ad_account_id not in {row["ad_account_id"] for row in rows}:
            raise UserError("The token cannot access that ad account; use an ID listed by doctor without --ad-account-id.")
        data["account"] = account(client, args.ad_account_id)
        data["account_access"] = "verified"
        if "APPSTORE_APP_MANUAL" not in data["account"]["product_features"]:
            data["warnings"].append("This ad account lacks APPSTORE_APP_MANUAL; App Store reports and insights may be unavailable.")
    return data


def apps(client, args):
    def fetch(offset, size):
        query = {"limit": size, "offset": offset}
        if args.query:
            query["query"] = args.query
        if args.owned:
            query["returnOwnedApps"] = "true"
        if args.storefront:
            query["storeFronts"] = args.storefront
        response = client.call("GET", "/search/apps", args.ad_account_id, query=query)
        return [{"adam_id": sid(a.get("adamId")), "app_name": a.get("appName"), "developer_name": a.get("developerName"),
                 "storefronts": a.get("countryOrRegionCodes") or []} for a in response.get("result") or []], total(response)

    rows, truncated, available = paged(fetch, args.limit, 100)
    return {"request": {"query": args.query, "owned": args.owned, "storefronts": args.storefront or [], "limit": args.limit},
            "results": rows, "truncated": truncated, "total_available": available}


def app(client, args):
    result = client.call("GET", f"/apps/{args.adam_id}", args.ad_account_id).get("result")
    if not isinstance(result, dict):
        raise UserError("No app returned for that Adam ID.")
    return {"results": {"adam_id": sid(result.get("id")), "app_name": result.get("appName"), "developer_name": result.get("artistName"),
                        "primary_language": result.get("primaryLanguage"), "primary_genre": result.get("primaryGenre"),
                        "secondary_genre": result.get("secondaryGenre"), "device_classes": result.get("deviceClasses") or [],
                        "is_preorder": result.get("isPreorder"), "available_storefronts": result.get("availableStorefronts") or []}}


def campaign_row(c, currencies):
    targeting = c.get("targeting") or {}
    return {"campaign_id": sid(c.get("id")), "name": c.get("name"), "promoted_object_type": c.get("promotedObjectType"),
            "adam_id": sid(c.get("promotedObjectId")), "status": c.get("status"), "display_status": c.get("displayStatus"),
            "system_status": c.get("systemStatus"), "system_status_reasons": c.get("systemStatusReasons") or [],
            "limiting_reasons": c.get("systemStatusLimitingReasons") or [],
            "countries": (targeting.get("countryOrRegion") or {}).get("include") or [],
            "supply_placements": (targeting.get("supplyPlacement") or {}).get("include") or [],
            "bid_strategy": (c.get("bidStrategy") or {}).get("bidStrategyType"), "daily_budget": money(c.get("dailyBudget"), currencies),
            "lifetime_budget": money(c.get("lifetimeBudget"), currencies), "billing_event": c.get("billingEvent"),
            "start_time": c.get("startTime"), "end_time": c.get("endTime"), "deleted": c.get("deleted")}


def campaigns(client, args):
    filters = []
    if args.adam_id:
        filters += [flt("promotedObjectType", "EQUALS", "APPSTORE_APP"), flt("promotedObjectId", "EQUALS", args.adam_id)]
    if args.status:
        filters.append(flt("status", "EQUALS", args.status))
    data = {"account": account(client, args.ad_account_id), "warnings": []}
    currencies = set()

    def fetch(offset, size):
        body = {"filters": filters, "sorting": [{"field": "id", "order": "ASC"}], "pagination": {"offset": offset, "pageSize": size, "fetchTotalCount": True}}
        response = client.call("POST", "/campaigns/query", args.ad_account_id, body)
        return [campaign_row(c, currencies) for c in response.get("result") or []], total(response)

    data["results"], data["truncated"], data["total_available"] = paged(fetch, args.limit, 1000)
    data["request"] = {"adam_id": args.adam_id, "status": args.status, "limit": args.limit}
    data["currency"] = single_currency(currencies, data["account"]["currency"], data["warnings"])
    return data


def report_row(level, row, group_by, currencies):
    meta = row.get("metadata") or {}
    if level == "keywords":
        out = {"keyword_id": sid(meta.get("id")), "keyword": meta.get("text"), "match_type": meta.get("matchType"), "status": meta.get("status"),
               "display_status": meta.get("displayStatus"), "bid": money(meta.get("bid"), currencies), "campaign_id": sid(meta.get("campaignId")),
               "ad_group_id": sid(meta.get("adGroupId")), "ad_group_name": (meta.get("adGroup") or {}).get("name"), "deleted": meta.get("deleted"),
               "bid_recommendation": decimal_text(((row.get("insights") or {}).get("bidRecommendation") or {}).get("suggestedBidAmount"))}
    elif level == "searchterms":
        keyword = meta.get("keyword") or {}
        out = {"search_term": meta.get("searchTermText"), "search_term_source": meta.get("searchTermSource"), "keyword_id": sid(keyword.get("id")),
               "keyword": keyword.get("text"), "match_type": keyword.get("matchType"), "campaign_id": sid(meta.get("campaignId")),
               "ad_group_id": sid(meta.get("adGroupId")), "ad_group_name": (meta.get("adGroup") or {}).get("name")}
    elif level == "adgroups":
        out = {"ad_group_id": sid(meta.get("id")), "ad_group_name": meta.get("name"), "campaign_id": sid(meta.get("campaignId")),
               "status": meta.get("status"), "display_status": meta.get("displayStatus"), "pricing_model": meta.get("pricingModel"),
               "bid_strategy": (meta.get("bidStrategy") or {}).get("bidStrategyType"), "automated_keywords_opt_in": meta.get("automatedKeywordsOptIn"),
               "deleted": meta.get("deleted")}
    else:
        out = {"campaign_id": sid(meta.get("id")), "campaign_name": meta.get("name"), "adam_id": sid(meta.get("promotedObjectId")),
               "status": meta.get("status"), "display_status": meta.get("displayStatus"), "ad_channel_type": meta.get("adChannelType"),
               "bid_strategy": (meta.get("bidStrategy") or {}).get("bidStrategyType"), "daily_budget": money(meta.get("dailyBudget"), currencies),
               "deleted": meta.get("deleted")}
    for dimension in group_by:
        out[SNAKE[dimension]] = meta.get(dimension)
    out.update(metrics(row.get("totalMetrics") or {}, currencies))
    out["granular"] = []
    for entry in row.get("granularMetrics") or []:
        # Apple documents dimensions in metadata, but some examples repeat them per period; keep either.
        period = {"date": entry.get("date"), **{SNAKE[d]: entry[d] for d in group_by if d in entry}}
        out["granular"].append({**period, **metrics(entry, currencies)})
    return out


def report(client, args):
    level, group_by = args.level, args.group_by or []
    filters = []
    if level != "campaigns":
        filters.append(flt("campaignId", "EQUALS", args.campaign_id[0]))
    elif args.campaign_id:
        filters.append(flt("campaignId", "IN", args.campaign_id))
    if args.ad_group_id:
        filters.append(flt("adGroupId", "EQUALS", args.ad_group_id))
    time_range = {"start": args.start.isoformat(), "end": args.end.isoformat(), "timeZone": args.time_zone.upper()}
    if args.granularity:
        time_range["granularity"] = args.granularity.upper()
    body = {"filters": filters, "timeRange": time_range, "options": {"includeRows": ["GRAND_TOTAL"] + (["EMPTY_METRICS"] if args.include_empty else [])}}
    if group_by:
        body["groupBy"] = group_by
    if args.sort:
        body["sorting"] = args.sort
    data = {"account": account(client, args.ad_account_id), "grand_total": None,
            "warnings": ["tap_* metrics are tap-through installs; total_* adds view-through installs. Compare like with like."]}
    currencies = set()

    def fetch(offset, size):
        body["pagination"] = {"offset": offset, "pageSize": size}
        response = client.call("POST", f"/reports/apps/{level}/query", args.ad_account_id, body)
        result = response.get("result") or {}
        grand = (result.get("summary") or {}).get("grandTotal")
        if grand and data["grand_total"] is None:
            data["grand_total"] = metrics(grand, currencies)
        return [report_row(level, row, group_by, currencies) for row in result.get("rows") or []], total(response)

    data["results"], data["truncated"], data["total_available"] = paged(fetch, args.limit, 5000)
    data["request"] = {"level": level, "campaign_ids": args.campaign_id or [], "ad_group_id": args.ad_group_id, "start": time_range["start"],
                       "end": time_range["end"], "time_zone": time_range["timeZone"], "granularity": time_range.get("granularity"),
                       "group_by": group_by, "sorting": args.sort or [], "include_empty": args.include_empty, "limit": args.limit}
    data["currency"] = single_currency(currencies, data["account"]["currency"], data["warnings"])
    unnamed = sum(1 for row in data["results"] if level == "searchterms" and not row["search_term"])
    if unnamed:
        data["warnings"].append(f"{unnamed} rows have no search term text; treat them as unattributed searches, not as one query.")
    return data


def suggestions(client, path, filters, args, field):
    def fetch(offset, size):
        body = {"filters": filters, "sorting": [{"field": "popularity", "order": "DESC"}], "pagination": {"offset": offset, "pageSize": size}}
        response = client.call("POST", path, args.ad_account_id, body)
        return [{field: r.get("text" if field == "keyword" else field), "popularity": r.get("popularity")} for r in response.get("result") or []], total(response)

    return paged(fetch, args.limit, 1000)


def ideas(client, args):
    filters = [flt("promotedObjectId", "EQUALS", [args.adam_id]), flt("promotedObjectType", "EQUALS", ["APPSTORE_APP"])]
    if args.terms:
        filters.append(flt("terms", "IN", args.terms))
    if args.country:
        filters.append(flt("countriesOrRegions", "IN", args.country))
    rows, truncated, available = suggestions(client, "/suggestions/keywords/query", filters, args, "keyword")
    warnings = ["Popularity is a relative 0-100 score, not search volume."]
    if len(args.country or []) != 1:
        warnings.append("Popularity spans all requested (or all) countries and regions; run one country per call to rank a market.")
    return {"request": {"adam_id": args.adam_id, "terms": args.terms, "countries": args.country or [], "limit": args.limit},
            "results": rows, "truncated": truncated, "total_available": available, "warnings": warnings}


def phrases(client, args):
    if args.adam_id:
        route, filters = "SUGGESTION", [flt("promotedObjectId", "EQUALS", [args.adam_id]), flt("promotedObjectType", "EQUALS", ["APPSTORE_APP"])]
    else:
        route, filters = "SEARCH", [flt("phrase", "IN", args.terms) if args.terms else flt("phrase", "LIKE", [args.like])]
    filters.append(flt("queryType", "EQUALS", [route]))
    rows, truncated, available = suggestions(client, "/suggestions/phrases/query", filters, args, "phrase")
    data = {"request": {"route": route, "adam_id": args.adam_id, "terms": args.terms, "like": args.like, "limit": args.limit},
            "results": rows, "truncated": truncated, "total_available": available,
            "warnings": ["Popularity is a relative score, not search volume. Apple's phrase endpoint takes no country filter."]}
    if args.terms:
        data["unmatched_terms"] = unmatched(args.terms, rows, "phrase", truncated, data["warnings"])
    return data


def unmatched(terms, rows, field, truncated, warnings):
    if truncated:
        warnings.append("Results are truncated, so unmatched_terms may list terms beyond --limit.")
    matched = {row[field].casefold() for row in rows if row[field]}
    return [term for term in terms if term.casefold() not in matched]


def insight_rows(client, path, body, args, normalize):
    def fetch(offset, size):
        body["pagination"] = {"offset": offset, "pageSize": size}
        response = client.call("POST", path, args.ad_account_id, body)
        return [normalize(r) for r in (response.get("result") or {}).get("rows") or []], total(response)

    return paged(fetch, args.limit, 5000)


def popularity(client, args):
    filters = [one_or_many("countryOrRegion", args.country)]
    if args.genre:
        filters.append(one_or_many("genre", args.genre))
    if args.terms:
        filters.append(flt("searchTerm", "IN", args.terms))
    if args.contains:
        filters.append(flt("searchTerm", "CONTAINS", args.contains))
    granularity = {"weekly": "WEEKLY_SUN_SAT", "monthly": "MONTHLY"}[args.granularity]
    body = {"fields": POPULARITY_FIELDS, "filters": filters,
            "timeRange": {"start": args.start.isoformat(), "end": args.end.isoformat(), "timeZone": "UTC", "granularity": granularity}}
    if args.sort:
        body["sorting"] = args.sort
    rows, truncated, available = insight_rows(client, "/insights/apps/search-term-popularity/query", body, args, lambda r: {
        "period": r.get("week") or r.get("month"), "country_or_region": r.get("countryOrRegion"), "genre": r.get("genre"),
        "search_term": r.get("searchTerm"), "rank_in_genre": r.get("rankInGenre"), "search_popularity_in_genre": r.get("searchPopularityInGenre"),
        "search_popularity_1to100": r.get("searchPopularity1to100"), "search_popularity_1to5": r.get("searchPopularity1to5")})
    data = {"request": {"countries": args.country, "genres": args.genre or [], "terms": args.terms, "contains": args.contains, "start": args.start.isoformat(),
                        "end": args.end.isoformat(), "time_zone": "UTC", "granularity": granularity, "sorting": args.sort or [], "limit": args.limit},
            "results": rows, "truncated": truncated, "total_available": available,
            "warnings": ["Relative popularity, not search counts. Apple lists terms with at least 500 searches and 10 impressions, "
                         "up to 500 per country or region and genre; a missing term is unknown, not zero demand."]}
    if args.terms:
        data["unmatched_terms"] = unmatched(args.terms, rows, "search_term", truncated, data["warnings"])
    return data


def impression_share(client, args):
    filters = [flt("promotedObjectId", "IN", args.adam_id)]
    if args.country:
        filters.append(one_or_many("countryOrRegion", args.country))
    if args.terms:
        filters.append(flt("searchTerm", "IN", args.terms))
    if args.contains:
        filters.append(flt("searchTerm", "CONTAINS", args.contains))
    granularity = {"daily": "DAILY", "weekly": "WEEKLY_SUN_SAT"}[args.granularity]
    slot = {"first": "FIRST_SLOT", "all": "ALL_SLOTS"}[args.slot]
    body = {"filters": filters, "options": {"impressionShareReportType": slot},
            "timeRange": {"start": args.start.isoformat(), "end": args.end.isoformat(), "timeZone": "UTC", "granularity": granularity}}
    if args.sort:
        body["sorting"] = args.sort
    rows, truncated, available = insight_rows(client, "/insights/apps/impression-share/query", body, args, lambda r: {
        "period": r.get("day") or r.get("week"), "adam_id": sid(r.get("promotedObjectId")), "app_name": r.get("appName"),
        "country_or_region": r.get("countryOrRegion"), "search_term": r.get("searchTerm"), "low_impression_share": r.get("lowImpressionShare"),
        "high_impression_share": r.get("highImpressionShare"), "rank": r.get("rank"), "search_popularity_1to5": r.get("searchPopularity1to5")})
    return {"request": {"adam_ids": args.adam_id, "countries": args.country or [], "terms": args.terms, "contains": args.contains,
                        "start": args.start.isoformat(), "end": args.end.isoformat(), "time_zone": "UTC", "granularity": granularity,
                        "slot": slot, "sorting": args.sort or [], "limit": args.limit},
            "results": rows, "truncated": truncated, "total_available": available,
            "warnings": ["Equal low/high shares are exact to one percent for 1-90%; 0.91/1.0 means above 90%. "
                         "Apple suppresses terms with fewer than 10 impressions."]}


HANDLERS = {"doctor": doctor, "apps": apps, "app": app, "campaigns": campaigns, "report": report, "ideas": ideas,
            "phrases": phrases, "popularity": popularity, "impression-share": impression_share}


def execute(client, args):
    data = {"command": args.command, "retrieved_at": datetime.now(timezone.utc).isoformat(), "api_version": API_VERSION}
    if args.ad_account_id:
        data["ad_account_id"] = args.ad_account_id
    data.update(HANDLERS[args.command](client, args))
    return data


def csv_text(data):
    rows = data["results"] if isinstance(data["results"], list) else [data["results"]]
    if data["command"] == "report" and data["request"]["granularity"]:
        # Long format for pivot tables: one line per entity and period.
        keys = set(METRICS.values()) | {"granular"}
        rows = [{**{k: v for k, v in row.items() if k not in keys}, **period} for row in rows for period in row["granular"]]
    else:
        rows = [{k: v for k, v in row.items() if k != "granular"} for row in rows]
    context = {"retrieved_at": data["retrieved_at"]}
    if data.get("currency"):
        context["currency"] = data["currency"]
    columns = list(dict.fromkeys(k for row in rows for k in row)) + list(context)
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: escape_formula(";".join(map(str, v)) if isinstance(v, list) else v) for k, v in {**row, **context}.items()})
    return out.getvalue()


def escape_formula(value):
    """Prevent spreadsheet formula execution for untrusted search-term and name strings."""
    if isinstance(value, str) and (value.startswith(("\t", "\r")) or value.lstrip().startswith(("=", "+", "-", "@"))):
        return "'" + value
    return value


def cell(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        value = ";".join(map(str, value))
    return "" if value is None else re.sub(r"\s*[\t\r\n]+\s*", " ", str(value))


SUMMARY_COLUMNS = {
    "doctor": ["ad_account_id", "name", "roles"],
    "apps": ["adam_id", "app_name", "developer_name"],
    "app": ["adam_id", "app_name", "primary_genre", "available_storefronts"],
    "campaigns": ["campaign_id", "name", "adam_id", "display_status", "daily_budget", "countries"],
    "ideas": ["keyword", "popularity"],
    "phrases": ["phrase", "popularity"],
    "popularity": ["period", "country_or_region", "genre", "search_term", "rank_in_genre", "search_popularity_1to100", "search_popularity_1to5"],
    "impression-share": ["period", "country_or_region", "search_term", "low_impression_share", "high_impression_share", "rank", "search_popularity_1to5"],
}
REPORT_COLUMNS = {"campaigns": ["campaign_id", "campaign_name"], "adgroups": ["ad_group_id", "ad_group_name"],
                  "keywords": ["keyword", "match_type", "status", "bid", "bid_recommendation"], "searchterms": ["search_term", "keyword", "match_type"]}
REPORT_METRICS = ["impressions", "taps", "local_spend", "tap_installs", "tap_install_cpi", "total_installs"]


def summary(data, outputs):
    """Compact TSV for stdout when full JSON goes to a file."""
    request = data.get("request") or {}
    meta = {"command": data["command"]}
    for key in ("ad_account_id", "token", "account_access", "currency"):
        if data.get(key) is not None:
            meta[key] = data[key]
    for key in ("level", "route", "countries", "start", "end", "time_zone", "granularity", "slot"):
        if request.get(key):
            meta[key] = request[key]
    results = data["results"]
    if isinstance(results, list):
        meta["rows"] = len(results)
    for key in ("truncated", "total_available"):
        if key in data:
            meta[key] = data[key]
    if "unmatched_terms" in data:
        meta["unmatched"] = len(data["unmatched_terms"])
    meta["outputs"] = ",".join(str(p) for p in outputs)
    lines = ["\t".join(f"{k}={cell(v)}" for k, v in meta.items())]
    if data["command"] == "report":
        columns = [SNAKE[d] for d in request["group_by"]] + REPORT_COLUMNS[request["level"]] + REPORT_METRICS
    else:
        columns = SUMMARY_COLUMNS[data["command"]]
    lines.append("\t".join(columns))
    lines.extend("\t".join(cell(row.get(c)) for c in columns) for row in (results if isinstance(results, list) else [results]))
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
        credentials = load_credentials(args)
        if credentials.key_path in [p.resolve() for p in (args.output, getattr(args, "csv", None)) if p]:
            raise UserError("Output paths must not overwrite the private key.")
        data = execute(Client(credentials), args)
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
        print(f"error: {type(exc).__name__}; no successful result emitted. Check output permissions and dependency compatibility.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
