"""Offline contract tests with a recorded fake transport and generated signing keys."""
import contextlib
import csv
import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apple_ads.py"
spec = importlib.util.spec_from_file_location("apple_ads", SCRIPT)
aa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aa)

ACCOUNT = {"result": {"id": 123, "name": "Acme", "currency": "USD", "timezone": "America/New_York", "systemStatus": "ACTIVE", "productFeatures": ["APPSTORE_APP_MANUAL"]}}


def pem(key, encryption=None):
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, encryption or serialization.NoEncryption())


def ok(payload, **headers):
    return 200, headers, payload


class Transport:
    """Answers the token endpoint itself and replays queued API responses in order."""

    def __init__(self, *responses, token_status=200):
        self.responses, self.token_status, self.requests = list(responses), token_status, []

    def __call__(self, method, url, headers, body):
        self.requests.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        if url == aa.TOKEN_URL:
            if self.token_status != 200:
                return self.token_status, {}, b'{"error": "invalid_client"}'
            return 200, {}, json.dumps({"access_token": f"token-{len(self.requests)}", "token_type": "Bearer", "expires_in": 3600}).encode()
        status, response_headers, payload = self.responses.pop(0)
        return status, response_headers, payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def api(self):
        return [r for r in self.requests if r["url"] != aa.TOKEN_URL]

    def tokens(self):
        return [r for r in self.requests if r["url"] == aa.TOKEN_URL]

    def body(self, index=-1):
        return json.loads(self.api()[index]["body"])


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.key = ec.generate_private_key(ec.SECP256R1())
        (self.dir / "key.pem").write_bytes(pem(self.key))
        self.config = self.dir / "apple-ads.toml"
        self.config.write_text('client_id = "SEARCHADS.client"\nteam_id = "SEARCHADS.team"\nkey_id = "key-1"\nprivate_key_path = "key.pem"\n')
        self.sleeps = []

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, command, *extra, account=True):
        argv = [command, "--config", str(self.config)] + (["--ad-account-id", "123"] if account else []) + list(extra)
        args = aa.parser().parse_args(argv)
        aa.prepare(args)
        return args

    def client(self, transport):
        return aa.Client(aa.load_credentials(self.args("doctor", account=False)), transport=transport, sleep=self.sleeps.append)

    def run_cli(self, argv, transport):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(aa, "urllib_transport", transport), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = aa.main([argv[0], "--config", str(self.config), *argv[1:]])
        return code, out.getvalue(), err.getvalue()


class AuthTests(Base):
    def test_client_secret_claims_and_signature(self):
        credentials = aa.load_credentials(self.args("doctor", account=False))
        secret = aa.client_secret(credentials, now=1_700_000_000)
        self.assertEqual(jwt.get_unverified_header(secret), {"alg": "ES256", "kid": "key-1", "typ": "JWT"})
        claims = jwt.decode(secret, self.key.public_key(), algorithms=["ES256"], audience="https://appleid.apple.com", options={"verify_exp": False})
        self.assertEqual(claims, {"sub": "SEARCHADS.client", "iss": "SEARCHADS.team", "aud": "https://appleid.apple.com", "iat": 1_700_000_000, "exp": 1_700_000_600})

    def test_config_errors_name_fields_not_values(self):
        self.config.write_text('client_id = "SEARCHADS.client"\nsecret = "x"\n')
        with self.assertRaisesRegex(aa.UserError, "Unknown configuration keys: secret"):
            aa.load_credentials(self.args("doctor", account=False))
        self.config.write_text('client_id = "SEARCHADS.client"\nkey_id = " "\n')
        with self.assertRaisesRegex(aa.UserError, "team_id, key_id, private_key_path"):
            aa.load_credentials(self.args("doctor", account=False))
        self.config.write_text("not toml =")
        with self.assertRaisesRegex(aa.UserError, "TOML"):
            aa.load_credentials(self.args("doctor", account=False))

    def test_environment_credentials(self):
        env = {"APPLE_ADS_CLIENT_ID": "SEARCHADS.env", "APPLE_ADS_TEAM_ID": "SEARCHADS.team", "APPLE_ADS_KEY_ID": "key-2",
               "APPLE_ADS_PRIVATE_KEY_PATH": str(self.dir / "key.pem")}
        args = aa.parser().parse_args(["doctor"])
        with patch.dict(os.environ, env):
            self.assertEqual(aa.load_credentials(args).client_id, "SEARCHADS.env")
        with patch.dict(os.environ, {**env, "APPLE_ADS_KEY_ID": ""}):
            with self.assertRaisesRegex(aa.UserError, "Missing Apple Ads credentials: key_id"):
                aa.load_credentials(args)

    def test_rejects_unusable_keys(self):
        keys = {
            "rsa": pem(rsa.generate_private_key(public_exponent=65537, key_size=2048)),
            "p384": pem(ec.generate_private_key(ec.SECP384R1())),
            "encrypted": pem(self.key, serialization.BestAvailableEncryption(b"passphrase")),
            "garbage": b"not a key",
        }
        for name, content in keys.items():
            with self.subTest(name=name):
                (self.dir / "key.pem").write_bytes(content)
                with self.assertRaises(aa.UserError) as raised:
                    aa.load_credentials(self.args("doctor", account=False))
                self.assertNotIn("BEGIN", str(raised.exception))
        (self.dir / "key.pem").unlink()
        with self.assertRaisesRegex(aa.UserError, "Cannot read"):
            aa.load_credentials(self.args("doctor", account=False))


class ClientTests(Base):
    def test_token_request_and_context_headers(self):
        transport = Transport(ok({"result": {"acls": []}}), ok(ACCOUNT))
        client = self.client(transport)
        client.call("GET", "/acls")
        client.call("GET", "/ad-accounts/123", "123")
        token = transport.tokens()[0]
        form = dict(urllib.parse.parse_qsl(token["body"].decode()))
        self.assertEqual(token["headers"]["Content-Type"], "application/x-www-form-urlencoded")
        self.assertEqual({k: form[k] for k in ("grant_type", "client_id", "scope")}, {"grant_type": "client_credentials", "client_id": "SEARCHADS.client", "scope": "searchadsorg"})
        jwt.decode(form["client_secret"], self.key.public_key(), algorithms=["ES256"], audience="https://appleid.apple.com")
        first, second = transport.api()
        self.assertEqual(first["url"], "https://api.ads.apple.com/v1/acls")
        self.assertEqual(first["headers"]["Authorization"], "Bearer token-1")
        self.assertNotIn("X-AP-Context", first["headers"])
        self.assertEqual(second["headers"]["X-AP-Context"], "adAccountId=123")
        self.assertEqual(len(transport.tokens()), 1)

    def test_read_only_guard(self):
        transport = Transport()
        client = self.client(transport)
        for method, path in [("PUT", "/campaigns/1"), ("POST", "/campaigns"), ("DELETE", "/keywords/1"), ("POST", "/keywords/bulk-create")]:
            with self.subTest(method=method, path=path), self.assertRaisesRegex(aa.UserError, "Refusing"):
                client.call(method, path, "123", {})
        self.assertEqual(transport.requests, [])

    def test_retries_rate_limits_and_server_errors(self):
        transport = Transport((429, {"retry-after": "3"}, {}), (503, {}, {}), ok({"result": {}}))
        self.assertEqual(self.client(transport).call("GET", "/acls"), {"result": {}})
        self.assertEqual(self.sleeps[0], 3)
        self.assertTrue(4 <= self.sleeps[1] <= 4.25)
        self.assertEqual(len(transport.api()), 3)

    def test_pacing_and_reset_fallback(self):
        transport = Transport((429, {"ratelimit-reset": "9"}, {}), ok({"result": {}}, **{"ratelimit-remaining": "2", "ratelimit-reset": "7"}))
        self.client(transport).call("GET", "/acls")
        self.assertEqual(self.sleeps, [9, 7])

    def test_expired_token_refreshes_once(self):
        transport = Transport((401, {}, {}), ok({"result": {}}))
        self.client(transport).call("GET", "/acls")
        self.assertEqual(len(transport.tokens()), 2)
        self.assertEqual(transport.api()[1]["headers"]["Authorization"], "Bearer token-3")
        transport = Transport((401, {}, {}), (401, {}, {"error": {"code": "UNAUTHORIZED"}}))
        with self.assertRaisesRegex(aa.UserError, "HTTP 401"):
            self.client(transport).call("GET", "/acls")

    def test_errors_are_summarized_without_secrets(self):
        error = {"error": {"code": "VALIDATION_ERROR", "message": "Validation\nerrors", "details": [{"code": "INVALID_DATE", "message": "too\x1b long", "info": {"field": "timeRange.end"}}]}}
        transport = Transport((400, {}, error))
        with self.assertRaises(aa.UserError) as raised:
            self.client(transport).call("POST", "/reports/apps/keywords/query", "123", {})
        message = str(raised.exception)
        self.assertIn("HTTP 400): VALIDATION_ERROR: Validation errors; INVALID_DATE on timeRange.end: too long", message)
        self.assertNotIn("token", message)
        self.assertEqual(len(transport.api()), 1)
        self.assertEqual(self.sleeps, [])

    def test_token_failure_and_network_failure(self):
        with self.assertRaises(aa.UserError) as raised:
            self.client(Transport(token_status=400)).call("GET", "/acls")
        self.assertIn("HTTP 400, invalid_client", str(raised.exception))
        self.assertNotIn("eyJ", str(raised.exception))

        def offline(*_):
            raise OSError("down")

        with self.assertRaisesRegex(aa.UserError, "Cannot reach Apple"):
            self.client(offline).call("GET", "/acls")
        self.assertEqual(len(self.sleeps), 3)

    def test_pagination_truncation_and_clamped_pages(self):
        data = list(range(10))
        calls = []

        def clamped(offset, size):
            calls.append((offset, size))
            return data[offset:offset + min(size, 3)], len(data)

        self.assertEqual(aa.paged(clamped, 20, 100), (data, False, 10))
        self.assertEqual(calls[0], (0, 21))
        self.assertEqual(aa.paged(clamped, 4, 100), ([0, 1, 2, 3], True, 10))
        self.assertEqual(aa.paged(lambda offset, size: (data[offset:offset + size], None), 10, 4), (data, False, None))
        self.assertEqual(aa.paged(lambda offset, size: (data[offset:offset + size], None), 9, 4), (data[:9], True, None))


class ReportTests(Base):
    def keyword_row(self, **meta):
        return {
            "metadata": {"id": 888, "text": "task manager", "matchType": "EXACT", "status": "ENABLED", "displayStatus": "RUNNING",
                         "bid": {"amount": "0.40", "currency": "USD"}, "campaignId": 444, "adGroupId": 555, "adGroup": {"name": "Exact"},
                         "deleted": False, "countryOrRegion": "US", **meta},
            "totalMetrics": {"localSpend": {"amount": "75.00", "currency": "USD"}, "impressions": 0, "taps": 250, "tapInstalls": 60,
                             "tapInstallCPI": {"amount": "1.25", "currency": "USD"}},
            "granularMetrics": [{"date": "2026-09-01", "localSpend": {"amount": "2.40", "currency": "USD"}, "taps": 8}],
            "insights": {"bidRecommendation": {"suggestedBidAmount": 2.35}},
        }

    def test_keyword_report_request_and_rows(self):
        response = {"result": {"rows": [self.keyword_row()], "summary": {"grandTotal": {"localSpend": {"amount": "75.00", "currency": "USD"}, "taps": 250}}},
                    "pagination": {"totalCount": 1, "offset": 0, "pageSize": 1001}}
        transport = Transport(ok(ACCOUNT), ok(response))
        args = self.args("report", "--level", "keywords", "--campaign-id", "444", "--ad-group-id", "555", "--start", "2026-09-01",
                         "--end", "2026-09-30", "--granularity", "daily", "--group-by", "countryOrRegion", "--sort", "localSpend:DESC")
        data = aa.execute(self.client(transport), args)
        self.assertTrue(transport.api()[1]["url"].endswith("/v1/reports/apps/keywords/query"))
        self.assertEqual(transport.body(), {
            "filters": [{"field": "campaignId", "operator": "EQUALS", "value": "444"}, {"field": "adGroupId", "operator": "EQUALS", "value": "555"}],
            "timeRange": {"start": "2026-09-01", "end": "2026-09-30", "timeZone": "ORTZ", "granularity": "DAILY"},
            "options": {"includeRows": ["GRAND_TOTAL"]}, "groupBy": ["countryOrRegion"],
            "sorting": [{"field": "localSpend", "order": "DESC"}], "pagination": {"offset": 0, "pageSize": 1001}})
        row = data["results"][0]
        self.assertEqual((row["keyword_id"], row["keyword"], row["bid"], row["ad_group_name"], row["country_or_region"]), ("888", "task manager", "0.40", "Exact", "US"))
        self.assertEqual((row["local_spend"], row["impressions"], row["tap_install_cpi"], row["total_installs"]), ("75.00", 0, "1.25", None))
        self.assertEqual(row["bid_recommendation"], "2.35")
        self.assertEqual(row["granular"][0]["date"], "2026-09-01")
        self.assertEqual(row["granular"][0]["local_spend"], "2.40")
        self.assertIsNone(row["granular"][0]["impressions"])
        self.assertEqual(data["grand_total"]["taps"], 250)
        self.assertEqual((data["currency"], data["truncated"], data["total_available"]), ("USD", False, 1))
        self.assertEqual(data["account"]["timezone"], "America/New_York")

    def test_report_validation(self):
        today = date.today()
        cases = {
            "campaign required": ["--level", "keywords", "--start", "2026-09-01", "--end", "2026-09-02"],
            "search terms in UTC": ["--level", "searchterms", "--campaign-id", "1", "--start", "2026-09-01", "--end", "2026-09-02", "--time-zone", "utc"],
            "hourly search terms": ["--level", "searchterms", "--campaign-id", "1", "--start", str(today - timedelta(days=2)), "--end", str(today), "--granularity", "hourly"],
            "old hourly": ["--level", "keywords", "--campaign-id", "1", "--start", str(today - timedelta(days=400)), "--end", str(today - timedelta(days=399)), "--granularity", "hourly"],
            "daily span": ["--level", "campaigns", "--start", "2026-01-01", "--end", "2026-04-01", "--granularity", "daily"],
            "weekly span": ["--level", "campaigns", "--start", "2026-01-01", "--end", "2026-01-13", "--granularity", "weekly"],
            "monthly span": ["--level", "campaigns", "--start", "2026-01-01", "--end", "2026-03-30", "--granularity", "monthly"],
            "empty with group": ["--level", "campaigns", "--start", "2026-09-01", "--end", "2026-09-02", "--include-empty", "--group-by", "deviceClass"],
            "keyword dimension": ["--level", "keywords", "--campaign-id", "1", "--start", "2026-09-01", "--end", "2026-09-02", "--group-by", "ageRange"],
            "ad group on campaigns": ["--level", "campaigns", "--ad-group-id", "2", "--start", "2026-09-01", "--end", "2026-09-02"],
            "two campaigns": ["--level", "keywords", "--campaign-id", "1", "--campaign-id", "2", "--start", "2026-09-01", "--end", "2026-09-02"],
            "reversed dates": ["--level", "campaigns", "--start", "2026-09-02", "--end", "2026-09-01"],
        }
        for name, extra in cases.items():
            with self.subTest(name), self.assertRaises(aa.UserError):
                self.args("report", *extra)
        for extra in (["--granularity", "daily", "--end", "2026-03-31"], ["--granularity", "weekly", "--end", "2026-01-14"], ["--granularity", "monthly", "--end", "2026-03-31"]):
            self.args("report", "--level", "campaigns", "--start", "2026-01-01", *extra)

    def test_campaign_level_filters_and_empty_result(self):
        transport = Transport(ok(ACCOUNT), ok({"result": {}, "pagination": {"totalCount": 0}}))
        args = self.args("report", "--level", "campaigns", "--campaign-id", "1", "--campaign-id", "2", "--start", "2026-09-01", "--end", "2026-09-01", "--include-empty")
        data = aa.execute(self.client(transport), args)
        body = transport.body()
        self.assertEqual(body["filters"], [{"field": "campaignId", "operator": "IN", "value": ["1", "2"]}])
        self.assertEqual(body["options"], {"includeRows": ["GRAND_TOTAL", "EMPTY_METRICS"]})
        self.assertNotIn("granularity", body["timeRange"])
        self.assertEqual((data["results"], data["grand_total"], data["truncated"]), ([], None, False))

    def test_search_terms_and_currency_warnings(self):
        rows = [{"metadata": {"searchTermText": term, "searchTermSource": "AUTO", "campaignId": 1, "adGroupId": 2, "adGroup": {"name": "Discovery"},
                              "keyword": {"id": 9, "text": "planner", "matchType": "BROAD"}},
                 "totalMetrics": {"localSpend": {"amount": "1.00", "currency": "USD"}}} for term in ("daily planner", None)]
        transport = Transport(ok({"result": {**ACCOUNT["result"], "currency": "EUR"}}), ok({"result": {"rows": rows}, "pagination": {"totalCount": 2}}))
        args = self.args("report", "--level", "searchterms", "--campaign-id", "1", "--start", "2026-09-01", "--end", "2026-09-07")
        data = aa.execute(self.client(transport), args)
        first = data["results"][0]
        self.assertEqual((first["search_term"], first["search_term_source"], first["keyword"], first["match_type"], first["ad_group_name"]),
                         ("daily planner", "AUTO", "planner", "BROAD", "Discovery"))
        self.assertTrue(any("1 rows have no search term text" in w for w in data["warnings"]))
        self.assertTrue(any("Mixed currencies returned (EUR, USD)" in w for w in data["warnings"]))


class ResearchTests(Base):
    def test_ideas_request_rows_and_market_warning(self):
        transport = Transport(ok({"result": [{"text": "task manager", "popularity": 72}, {"text": "todo", "popularity": 0}], "pagination": {"totalCount": 2}}))
        data = aa.execute(self.client(transport), self.args("ideas", "--adam-id", "999", "--term", "tasks", "--term", "tasks"))
        self.assertEqual(transport.body(), {
            "filters": [{"field": "promotedObjectId", "operator": "EQUALS", "value": ["999"]}, {"field": "promotedObjectType", "operator": "EQUALS", "value": ["APPSTORE_APP"]},
                        {"field": "terms", "operator": "IN", "value": ["tasks"]}],
            "sorting": [{"field": "popularity", "order": "DESC"}], "pagination": {"offset": 0, "pageSize": 201}})
        self.assertEqual(data["results"], [{"keyword": "task manager", "popularity": 72}, {"keyword": "todo", "popularity": 0}])
        self.assertTrue(any("one country per call" in w for w in data["warnings"]))
        transport = Transport(ok({"result": [], "pagination": {"totalCount": 0}}))
        data = aa.execute(self.client(transport), self.args("ideas", "--adam-id", "999", "--country", "de"))
        self.assertEqual(transport.body()["filters"][-1], {"field": "countriesOrRegions", "operator": "IN", "value": ["DE"]})
        self.assertFalse(any("one country per call" in w for w in data["warnings"]))

    def test_phrase_routes(self):
        for extra in ([], ["--adam-id", "1", "--like", "x"]):
            with self.subTest(extra=extra), self.assertRaisesRegex(aa.UserError, "exactly one"):
                self.args("phrases", *extra)
        transport = Transport(ok({"result": [{"phrase": "Best Planner", "popularity": 40}]}))
        data = aa.execute(self.client(transport), self.args("phrases", "--term", "best planner", "--term", "rare phrase"))
        self.assertEqual(transport.body()["filters"], [{"field": "phrase", "operator": "IN", "value": ["best planner", "rare phrase"]},
                                                       {"field": "queryType", "operator": "EQUALS", "value": ["SEARCH"]}])
        self.assertEqual(data["unmatched_terms"], ["rare phrase"])
        transport = Transport(ok({"result": []}))
        aa.execute(self.client(transport), self.args("phrases", "--like", "plan"))
        self.assertEqual(transport.body()["filters"][0], {"field": "phrase", "operator": "LIKE", "value": ["plan"]})
        transport = Transport(ok({"result": []}))
        aa.execute(self.client(transport), self.args("phrases", "--adam-id", "999"))
        self.assertEqual(transport.body()["filters"][-1]["value"], ["SUGGESTION"])

    def test_popularity_request_rows_and_unmatched(self):
        rows = [{"month": "2026-08", "countryOrRegion": "US", "genre": "PRODUCTIVITY_UTILITIES", "searchTerm": "task manager",
                 "rankInGenre": 1, "searchPopularityInGenre": 95, "searchPopularity1to100": 88, "searchPopularity1to5": 5}]
        transport = Transport(ok({"result": {"rows": rows}, "pagination": {"offset": 0, "pageSize": 1001}}))
        args = self.args("popularity", "--country", "us", "--genre", "PRODUCTIVITY_UTILITIES", "--granularity", "monthly",
                         "--start", "2026-06-01", "--end", "2026-08-31", "--term", "task manager", "--term", "habit tracker")
        data = aa.execute(self.client(transport), args)
        self.assertTrue(transport.api()[0]["url"].endswith("/v1/insights/apps/search-term-popularity/query"))
        self.assertEqual(transport.body(), {
            "fields": ["rankInGenre", "searchPopularityInGenre", "searchPopularity1to100", "searchPopularity1to5"],
            "filters": [{"field": "countryOrRegion", "operator": "EQUALS", "value": "US"}, {"field": "genre", "operator": "EQUALS", "value": "PRODUCTIVITY_UTILITIES"},
                        {"field": "searchTerm", "operator": "IN", "value": ["task manager", "habit tracker"]}],
            "timeRange": {"start": "2026-06-01", "end": "2026-08-31", "timeZone": "UTC", "granularity": "MONTHLY"},
            "pagination": {"offset": 0, "pageSize": 1001}})
        self.assertEqual(data["results"][0], {"period": "2026-08", "country_or_region": "US", "genre": "PRODUCTIVITY_UTILITIES", "search_term": "task manager",
                                              "rank_in_genre": 1, "search_popularity_in_genre": 95, "search_popularity_1to100": 88, "search_popularity_1to5": 5})
        self.assertEqual(data["unmatched_terms"], ["habit tracker"])
        transport = Transport(ok({"result": {"rows": []}}))
        aa.execute(self.client(transport), self.args("popularity", "--country", "US", "--country", "GB", "--granularity", "weekly",
                                                     "--start", "2026-09-06", "--end", "2026-09-12", "--contains", "task"))
        self.assertEqual(transport.body()["filters"], [{"field": "countryOrRegion", "operator": "IN", "value": ["US", "GB"]},
                                                       {"field": "searchTerm", "operator": "CONTAINS", "value": "task"}])
        with self.assertRaisesRegex(aa.UserError, "not both"):
            self.args("popularity", "--country", "US", "--granularity", "weekly", "--start", "2026-09-06", "--end", "2026-09-12", "--contains", "a", "--term", "b")

    def test_impression_share_validation_body_and_rows(self):
        for extra in (["--granularity", "daily", "--start", "2026-09-01", "--end", "2026-10-01"],
                      ["--granularity", "weekly", "--start", "2026-09-07", "--end", "2026-09-19"],
                      ["--granularity", "weekly", "--start", "2026-09-06", "--end", "2026-10-04"]):
            with self.subTest(extra=extra), self.assertRaises(aa.UserError):
                self.args("impression-share", "--adam-id", "111", *extra)
        row = {"week": "2026-09-06", "appName": "Acme", "promotedObjectId": "111", "countryOrRegion": "US", "searchTerm": "acme",
               "lowImpressionShare": 0.91, "highImpressionShare": 1.0, "rank": 1, "searchPopularity1to5": 2}
        transport = Transport(ok({"result": {"rows": [row]}, "pagination": {"totalCount": 1}}))
        args = self.args("impression-share", "--adam-id", "111", "--country", "US", "--granularity", "weekly", "--slot", "all",
                         "--start", "2026-09-06", "--end", "2026-10-03", "--sort", "highImpressionShare:desc")
        data = aa.execute(self.client(transport), args)
        self.assertEqual(transport.body(), {
            "filters": [{"field": "promotedObjectId", "operator": "IN", "value": ["111"]}, {"field": "countryOrRegion", "operator": "EQUALS", "value": "US"}],
            "options": {"impressionShareReportType": "ALL_SLOTS"},
            "timeRange": {"start": "2026-09-06", "end": "2026-10-03", "timeZone": "UTC", "granularity": "WEEKLY_SUN_SAT"},
            "sorting": [{"field": "highImpressionShare", "order": "DESC"}], "pagination": {"offset": 0, "pageSize": 1001}})
        self.assertEqual((data["results"][0]["period"], data["results"][0]["low_impression_share"], data["results"][0]["high_impression_share"]), ("2026-09-06", 0.91, 1.0))

    def test_lookup_commands(self):
        transport = Transport(ok({"result": [{"adamId": 1, "appName": "Acme", "developerName": "Acme Inc.", "countryOrRegionCodes": ["US"]}], "pagination": {"totalCount": 1}}))
        data = aa.execute(self.client(transport), self.args("apps", "--owned", "--storefront", "us"))
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(transport.api()[0]["url"]).query))
        self.assertEqual(query, {"limit": "51", "offset": "0", "returnOwnedApps": "true", "storeFronts": "US"})
        self.assertEqual(data["results"][0]["adam_id"], "1")
        with self.assertRaisesRegex(aa.UserError, "--query, --owned"):
            self.args("apps")
        details = {"id": "1", "appName": "Acme", "artistName": "Acme Inc.", "primaryGenre": "Productivity", "availableStorefronts": ["US", "DE"]}
        data = aa.execute(self.client(Transport(ok({"result": details}))), self.args("app", "--adam-id", "1"))
        self.assertEqual((data["results"]["primary_genre"], data["results"]["available_storefronts"]), ("Productivity", ["US", "DE"]))
        campaign = {"id": 444, "name": "Brand", "promotedObjectType": "APPSTORE_APP", "promotedObjectId": "1", "displayStatus": "RUNNING",
                    "targeting": {"countryOrRegion": {"include": ["US"]}}, "dailyBudget": {"value": {"amount": "100.00", "currency": "USD"}},
                    "bidStrategy": {"bidStrategyType": "MANUAL_CPT"}}
        transport = Transport(ok(ACCOUNT), ok({"result": [campaign], "pagination": {"totalCount": 1}}))
        data = aa.execute(self.client(transport), self.args("campaigns", "--adam-id", "1", "--status", "ENABLED"))
        self.assertEqual(transport.body()["filters"], [{"field": "promotedObjectType", "operator": "EQUALS", "value": "APPSTORE_APP"},
                                                       {"field": "promotedObjectId", "operator": "EQUALS", "value": "1"},
                                                       {"field": "status", "operator": "EQUALS", "value": "ENABLED"}])
        self.assertTrue(transport.body()["pagination"]["fetchTotalCount"])
        self.assertEqual((data["results"][0]["countries"], data["results"][0]["daily_budget"], data["currency"]), (["US"], "100.00", "USD"))

    def test_doctor_lists_and_verifies_accounts(self):
        acls = {"result": {"acls": [{"adAccount": {"id": 123, "name": "Acme", "orgId": 9}, "roles": ["API Account Read Only"]}]}}
        data = aa.execute(self.client(Transport(ok(acls))), self.args("doctor", account=False))
        self.assertEqual(data["results"], [{"ad_account_id": "123", "name": "Acme", "org_id": "9", "roles": ["API Account Read Only"]}])
        self.assertNotIn("account_access", data)
        maps = {"result": {**ACCOUNT["result"], "productFeatures": ["BUSINESS_BRAND_MANUAL"]}}
        data = aa.execute(self.client(Transport(ok(acls), ok(maps))), self.args("doctor"))
        self.assertEqual(data["account_access"], "verified")
        self.assertTrue(any("APPSTORE_APP_MANUAL" in w for w in data["warnings"]))
        with self.assertRaisesRegex(aa.UserError, "cannot access"):
            aa.execute(self.client(Transport(ok({"result": {"acls": []}}))), self.args("doctor"))


class OutputTests(Base):
    def report_response(self):
        row = {"metadata": {"id": 1, "text": "=HYPERLINK(1)", "matchType": "EXACT"},
               "totalMetrics": {"taps": 3, "localSpend": {"amount": "3.00", "currency": "USD"}},
               "granularMetrics": [{"date": "2026-09-01", "taps": 1}, {"date": "2026-09-02", "taps": 2}]}
        return Transport(ok(ACCOUNT), ok({"result": {"rows": [row]}, "pagination": {"totalCount": 1}}))

    def test_cli_writes_json_csv_and_summary(self):
        out, sheet = self.dir / "report.json", self.dir / "report.csv"
        code, stdout, stderr = self.run_cli(["report", "--ad-account-id", "123", "--level", "keywords", "--campaign-id", "4", "--start", "2026-09-01",
                                             "--end", "2026-09-02", "--granularity", "daily", "--output", str(out), "--csv", str(sheet)], self.report_response())
        self.assertEqual((code, stderr), (0, ""))
        header, columns, line = stdout.splitlines()
        self.assertIn("command=report\tad_account_id=123\tcurrency=USD\tlevel=keywords", header)
        self.assertIn("rows=1\ttruncated=false\ttotal_available=1", header)
        self.assertEqual(columns.split("\t")[:3], ["keyword", "match_type", "status"])
        self.assertTrue(line.startswith("=HYPERLINK(1)\tEXACT"))
        self.assertEqual(json.loads(out.read_text())["results"][0]["keyword"], "=HYPERLINK(1)")
        rows = list(csv.DictReader(io.StringIO(sheet.read_text(encoding="utf-8"))))
        self.assertEqual([(r["date"], r["taps"], r["keyword"], r["currency"]) for r in rows],
                         [("2026-09-01", "1", "'=HYPERLINK(1)", "USD"), ("2026-09-02", "2", "'=HYPERLINK(1)", "USD")])
        self.assertNotIn("granular", rows[0])

    def test_totals_csv_without_granularity_joins_lists(self):
        sheet = self.dir / "campaigns.csv"
        campaign = {"id": 4, "name": "Brand", "targeting": {"countryOrRegion": {"include": ["US", "GB"]}}}
        transport = Transport(ok(ACCOUNT), ok({"result": [campaign], "pagination": {"totalCount": 1}}))
        code, stdout, _ = self.run_cli(["campaigns", "--ad-account-id", "123", "--csv", str(sheet)], transport)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["results"][0]["countries"], ["US", "GB"])
        self.assertEqual(next(csv.DictReader(io.StringIO(sheet.read_text(encoding="utf-8"))))["countries"], "US;GB")

    def test_output_path_safety(self):
        base = ["ideas", "--ad-account-id", "123", "--adam-id", "1"]
        cases = [["--output", str(self.dir / "x.json"), "--csv", str(self.dir / "x.json")], ["--output", str(self.config)],
                 ["--output", str(self.dir / "key.pem")], ["--output", str(self.dir / "missing" / "x.json")]]
        for extra in cases:
            with self.subTest(extra=extra):
                code, stdout, stderr = self.run_cli(base + extra, Transport())
                self.assertEqual((code, stdout), (1, ""))
                self.assertTrue(stderr.startswith("error: "))
        self.assertIn("private key", self.run_cli(base + ["--output", str(self.dir / "key.pem")], Transport())[2])
        self.assertTrue((self.dir / "key.pem").read_bytes().startswith(b"-----BEGIN PRIVATE KEY-----"))

    def test_api_failure_emits_no_dataset(self):
        transport = Transport((403, {}, {"error": {"code": "FORBIDDEN", "message": "Insufficient role"}}))
        out = self.dir / "ideas.json"
        code, stdout, stderr = self.run_cli(["ideas", "--ad-account-id", "123", "--adam-id", "1", "--output", str(out)], transport)
        self.assertEqual((code, stdout), (1, ""))
        self.assertIn("HTTP 403): FORBIDDEN: Insufficient role. Check the API user's role", stderr)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
