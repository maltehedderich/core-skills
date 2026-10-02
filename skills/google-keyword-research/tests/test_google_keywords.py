"""Offline contract tests with real Google Ads protobufs and mocked transports."""
import contextlib
import importlib.util
import io
import json
import logging
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.ads.googleads.v25.services.services.keyword_plan_idea_service.pagers import GenerateKeywordIdeasPager
from google.api_core import exceptions
from google.auth.credentials import AnonymousCredentials

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "google_keywords.py"
spec = importlib.util.spec_from_file_location("google_keywords", SCRIPT)
kw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kw)


class KeywordTests(unittest.TestCase):
    def setUp(self):
        self.sdk = GoogleAdsClient(credentials=AnonymousCredentials(), use_proto_plus=True, version="v25")
        self.service = Mock()
        self.client = SimpleNamespace(get_type=self.sdk.get_type, enums=self.sdk.enums, get_service=Mock(return_value=self.service))
        self.calls = kw.Calls(sleep=lambda _: None)

    def args(self, command="metrics", *extra):
        argv = [command, "--customer-id", "123-456-7890"]
        if command in ("ideas", "metrics"):
            argv += ["--geo-id", "2276", "--language-id", "1001"]
        args = kw.parser().parse_args(argv + list(extra))
        kw.prepare(args)
        return args

    def result(self, kind="historical", text="Zeiterfassung"):
        name, attr = ("GenerateKeywordHistoricalMetricsResult", "keyword_metrics") if kind == "historical" else ("GenerateKeywordIdeaResult", "keyword_idea_metrics")
        r = self.sdk.get_type(name)
        r.text = text
        m = getattr(r, attr)
        m.avg_monthly_searches = 0
        m.competition = self.sdk.enums.KeywordPlanCompetitionLevelEnum.LOW
        m.low_top_of_page_bid_micros = 1234567
        for year, month, searches in [(2026, 3, 0), (2025, 13, 8)]:
            item = self.sdk.get_type("MonthlySearchVolume")
            item.year, item.month, item.monthly_searches = year, month, searches
            m.monthly_search_volumes.append(item)
        return r

    def page(self, words, next_token=""):
        response = self.sdk.get_type("GenerateKeywordIdeaResponse")
        response.results.extend(self.result("idea", word) for word in words)
        response.next_page_token = next_token
        return GenerateKeywordIdeasPager(
            method=Mock(side_effect=AssertionError("CLI must pace page fetches itself")),
            request=self.sdk.get_type("GenerateKeywordIdeasRequest"),
            response=response,
        )

    def test_missing_zero_money_and_months(self):
        r = self.result()
        r.close_variants.append("Zeiterfassungen")
        # Missing monthly values must also stay missing.
        month = self.sdk.get_type("MonthlySearchVolume")
        month.year, month.month = 2026, 4
        r.keyword_metrics.monthly_search_volumes.append(month)
        row = kw.normalize(r, "keyword_metrics")
        self.assertEqual(row["avg_monthly_searches"], 0)
        self.assertIsNone(row["competition_index"])
        self.assertIsNone(row["high_top_of_page_bid"])
        self.assertEqual(row["low_top_of_page_bid"], "1.234567")
        self.assertEqual(row["close_variants"], ["Zeiterfassungen"])
        self.assertEqual(row["monthly_search_volumes"], [{"month": "2025-12", "searches": 8}, {"month": "2026-02", "searches": 0}, {"month": "2026-03", "searches": None}])

    def test_empty_metrics_are_unknown(self):
        r = self.sdk.get_type("GenerateKeywordIdeaResult")
        r.text = "unknown"
        row = kw.normalize(r, "keyword_idea_metrics")
        self.assertIsNone(row["avg_monthly_searches"])
        self.assertIsNone(row["competition"])
        self.assertEqual(row["monthly_search_volumes"], [])

    def test_each_idea_seed_and_targeting(self):
        for extra, seed in [(["--keyword", "tracking"], "keyword_seed"), (["--url", "https://example.com"], "url_seed"), (["--keyword", "tracking", "--url", "https://example.com"], "keyword_and_url_seed")]:
            with self.subTest(seed=seed):
                self.service.generate_keyword_ideas.return_value = self.page([])
                kw.ideas(self.client, self.calls, self.args("ideas", *extra))
                request = self.service.generate_keyword_ideas.call_args.kwargs["request"]
                self.assertEqual(request._pb.WhichOneof("seed"), seed)
                self.assertEqual(request.customer_id, "1234567890")
                self.assertEqual(request.language, "languageConstants/1001")
                self.assertEqual(list(request.geo_target_constants), ["geoTargetConstants/2276"])
                self.assertEqual(request.keyword_plan_network.name, "GOOGLE_SEARCH")

    def test_worldwide_and_partners(self):
        args = kw.parser().parse_args(["metrics", "--customer-id", "1234567890", "--keyword", "tracking", "--worldwide", "--language-id", "1000", "--network", "google-and-partners"])
        kw.prepare(args)
        request = self.sdk.get_type("GenerateKeywordHistoricalMetricsRequest")
        kw.targeting(self.client, request, args)
        self.assertEqual(list(request.geo_target_constants), [])
        self.assertEqual(request.keyword_plan_network.name, "GOOGLE_SEARCH_AND_PARTNERS")

    def test_pagination_limit_and_tokens(self):
        tokens, sizes = [], []
        pages = [self.page(["one"], "next"), self.page(["two", "three"])]
        pages[0]._response.total_size = 57
        pages[1]._response.total_size = 3
        def fetch(**kwargs):
            tokens.append(kwargs["request"].page_token)
            sizes.append(kwargs["request"].page_size)
            return pages.pop(0)
        self.service.generate_keyword_ideas.side_effect = fetch
        rows, truncated, total = kw.ideas(self.client, self.calls, self.args("ideas", "--keyword", "seed", "--limit", "2"))
        self.assertEqual([r["keyword"] for r in rows], ["one", "two"])
        self.assertTrue(truncated)
        self.assertEqual(tokens, ["", "next"])
        self.assertEqual(sizes, [3, 3])
        self.assertEqual(total, 57)

    def test_limit_at_exact_end_not_truncated(self):
        self.service.generate_keyword_ideas.return_value = self.page(["one", "two"])
        _, truncated, total = kw.ideas(self.client, self.calls, self.args("ideas", "--keyword", "seed", "--limit", "2"))
        self.assertFalse(truncated)
        self.assertIsNone(total)

    def test_average_cpc_and_concepts(self):
        request = self.sdk.get_type("GenerateKeywordHistoricalMetricsRequest")
        kw.targeting(self.client, request, self.args("metrics", "--keyword", "x"))
        self.assertTrue(request.historical_metrics_options.include_average_cpc)
        self.assertFalse(request.historical_metrics_options._pb.HasField("year_month_range"))
        idea = self.result("idea", "asana alternative")
        idea.keyword_idea_metrics.average_cpc_micros = 2_500_000
        for name, group, kind in (("Asana", "Others", "OTHER_BRANDS"), ("Alternative", "Comparison", "NON_BRAND"), ("Misc", "", "UNKNOWN")):
            item = self.sdk.get_type("KeywordConcept")
            item.name, item.concept_group.name = name, group
            item.concept_group.type_ = getattr(self.sdk.enums.KeywordPlanConceptGroupTypeEnum, kind)
            idea.keyword_annotations.concepts.append(item)
        row = kw.normalize(idea, "keyword_idea_metrics")
        self.assertEqual(row["average_cpc_micros"], 2_500_000)
        self.assertEqual(row["average_cpc"], "2.5")
        self.assertEqual(row["concepts"], [{"name": "Asana", "group": "Others", "group_type": "OTHER_BRANDS"},
                                           {"name": "Alternative", "group": "Comparison", "group_type": "NON_BRAND"},
                                           {"name": "Misc", "group": "", "group_type": None}])
        historical = kw.normalize(self.result(), "keyword_metrics")
        self.assertIsNone(historical["average_cpc"])
        self.assertNotIn("concepts", historical)

    def test_ideas_request_concepts_and_site_seed(self):
        self.service.generate_keyword_ideas.return_value = self.page([])
        kw.ideas(self.client, self.calls, self.args("ideas", "--site", "Example.COM"))
        request = self.service.generate_keyword_ideas.call_args.kwargs["request"]
        self.assertEqual(request._pb.WhichOneof("seed"), "site_seed")
        self.assertEqual(request.site_seed.site, "example.com")
        self.assertEqual([a.name for a in request.keyword_annotation], ["KEYWORD_CONCEPT"])
        for extra in (["--keyword", "x"], ["--url", "https://example.com"]):
            with self.subTest(extra=extra), self.assertRaises(kw.UserError):
                self.args("ideas", "--site", "example.com", *extra)
        for site in ("https://example.com", "example.com/path", "user@example.com", "example.com:443", "localhost", "a..com"):
            with self.subTest(site=site), self.assertRaises(kw.UserError):
                self.args("ideas", "--site", site)

    def test_custom_historical_window(self):
        args = self.args("metrics", "--keyword", "x", "--from-month", "2025-01", "--to-month", "2025-12")
        request = self.sdk.get_type("GenerateKeywordHistoricalMetricsRequest")
        kw.targeting(self.client, request, args)
        window = request.historical_metrics_options.year_month_range
        self.assertEqual((window.start.year, window.start.month.name), (2025, "JANUARY"))
        self.assertEqual((window.end.year, window.end.month.name), (2025, "DECEMBER"))
        self.service.generate_keyword_historical_metrics.return_value = self.sdk.get_type("GenerateKeywordHistoricalMetricsResponse")
        with patch.object(kw, "account", return_value={"test_account": False, "currency_code": "EUR"}):
            data = kw.execute(self.client, self.calls, args)
        self.assertEqual(data["request"]["period"], "2025-01 to 2025-12")
        today = date.today()
        current = f"{today.year:04d}-{today.month:02d}"
        for extra in (["--from-month", "2025-01"], ["--to-month", "2025-01"], ["--from-month", "2025-02", "--to-month", "2025-01"],
                      ["--from-month", "2025-01", "--to-month", current]):
            with self.subTest(extra=extra), self.assertRaises(kw.UserError):
                self.args("metrics", "--keyword", "x", *extra)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.args("metrics", "--keyword", "x", "--from-month", "2025-13", "--to-month", "2025-12")

    def test_historical_grouping_unmatched_and_batches(self):
        args = self.args("metrics", "--keyword", "car", "--keyword", "cars", "--keyword", "missing")
        result = self.result(text="car")
        result.close_variants.append("cars")
        response = self.sdk.get_type("GenerateKeywordHistoricalMetricsResponse")
        response.results.append(result)
        self.service.generate_keyword_historical_metrics.return_value = response
        rows, unmatched = kw.metrics(self.client, self.calls, args)
        self.assertEqual(len(rows), 1)
        self.assertEqual(unmatched, ["missing"])
        args.keywords = [str(i) for i in range(10001)]
        sizes = []
        def fetch(**kwargs):
            sizes.append(len(kwargs["request"].keywords))
            return self.sdk.get_type("GenerateKeywordHistoricalMetricsResponse")
        self.service.generate_keyword_historical_metrics.side_effect = fetch
        kw.metrics(self.client, self.calls, args)
        self.assertEqual(sizes, [10000, 1])

    def test_no_export_after_later_batch_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / "keywords.txt", Path(temp) / "out.json"
            source.write_text("\n".join(str(i) for i in range(10001)), encoding="utf-8")
            output.write_text("previous successful export", encoding="utf-8")
            self.service.generate_keyword_historical_metrics.side_effect = [self.sdk.get_type("GenerateKeywordHistoricalMetricsResponse"), exceptions.PermissionDenied("SECRET")]
            with patch.object(kw, "load_client", return_value=self.client), patch.object(kw, "account", return_value={"currency_code": "EUR", "test_account": False}), contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = kw.main(["metrics", "--customer-id", "1234567890", "--keywords-file", str(source), "--geo-id", "2276", "--language-id", "1001", "--output", str(output)])
            self.assertEqual(code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertNotIn("SECRET", stderr.getvalue())
            self.assertEqual(output.read_text(), "previous successful export")

    def test_retry_pacing_and_bound(self):
        now = [0.0]
        def sleep(delay):
            now[0] += delay
        calls = kw.Calls(sleep=sleep, clock=lambda: now[0])
        starts = []
        def call():
            starts.append(now[0])
            if len(starts) < 3:
                raise exceptions.ServiceUnavailable("SECRET")
            return "ok"
        self.assertEqual(calls.run(call, planning=True), "ok")
        calls.run(lambda: starts.append(now[0]), planning=True)
        self.assertTrue(all(b - a >= 1.05 - 1e-9 for a, b in zip(starts, starts[1:])))
        bad = Mock(side_effect=exceptions.ResourceExhausted("SECRET"))
        with self.assertRaises(kw.UserError) as error:
            calls.run(bad, planning=True)
        self.assertEqual(bad.call_count, 3)
        self.assertNotIn("SECRET", str(error.exception))

    def test_google_ads_error_codes_without_messages(self):
        failure = self.sdk.get_type("GoogleAdsFailure")
        error = self.sdk.get_type("GoogleAdsError")
        enum = error.error_code._pb.DESCRIPTOR.fields_by_name["authorization_error"].enum_type
        error.error_code.authorization_error = enum.values_by_name["USER_PERMISSION_DENIED"].number
        error.message = "SECRET"
        failure.errors.append(error)
        exc = GoogleAdsException(Mock(), Mock(), failure, "safe-request-id")
        bad = Mock(side_effect=exc)
        with self.assertRaises(kw.UserError) as caught:
            self.calls.run(bad)
        self.assertEqual(bad.call_count, 1)
        self.assertIn("USER_PERMISSION_DENIED", str(caught.exception))
        self.assertIn("safe-request-id", str(caught.exception))
        self.assertNotIn("SECRET", str(caught.exception))

    def test_token_free_environment_and_yaml(self):
        settings = {"GOOGLE_ADS_CLIENT_ID": "id", "GOOGLE_ADS_CLIENT_SECRET": "secret", "GOOGLE_ADS_REFRESH_TOKEN": "token", "GOOGLE_ADS_USE_PROTO_PLUS": "true"}
        with patch.dict(os.environ, settings, clear=True), patch("google.ads.googleads.oauth2.get_credentials", return_value=AnonymousCredentials()):
            client = kw.load_client(self.args("doctor"))
            self.assertIsNone(client.developer_token)
            self.assertTrue(client.use_proto_plus)
            self.assertTrue(logging.getLogger("google.ads.googleads.client").disabled)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "credentials.yaml"
            path.write_text("client_id: id\nclient_secret: secret\nrefresh_token: token\nuse_proto_plus: true\nlogging:\n  version: 1\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch("google.ads.googleads.oauth2.get_credentials", return_value=AnonymousCredentials()), patch("logging.config.dictConfig") as log_config:
                client = kw.load_client(self.args("doctor", "--config", str(path)))
                self.assertIsNone(client.developer_token)
                log_config.assert_not_called()

    def test_missing_configuration_and_implicit_path(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(kw.UserError):
                kw.load_client(self.args("doctor"))
        with patch.dict(os.environ, {"GOOGLE_ADS_CONFIGURATION_FILE_PATH": "SECRET"}, clear=True):
            with self.assertRaises(kw.UserError) as caught:
                kw.load_client(self.args("doctor"))
            self.assertNotIn("SECRET", str(caught.exception))

    def test_validation_and_file_unicode(self):
        for command, extra in [("ideas", []), ("metrics", []), ("ideas", ["--url", "https://user:secret@example.com"]), ("ideas", [item for i in range(21) for item in ("--keyword", str(i))]), ("doctor", ["--check-planning"]), ("doctor", ["--keyword", "unused"])]:
            with self.subTest(command=command, extra=extra), self.assertRaises(kw.UserError):
                self.args(command, *extra)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "keywords.txt"
            path.write_text("\ufeffÜbersicht\n\n时间\nÜbersicht\n", encoding="utf-8")
            args = self.args("metrics", "--keywords-file", str(path))
            self.assertEqual(args.keywords, ["Übersicht", "时间"])
            with self.assertRaises(kw.UserError):
                self.args("metrics", "--keywords-file", str(path), "--output", str(path))

    def test_json_csv_and_empty_output(self):
        data = {"command": "metrics", "account": {"currency_code": "EUR"}, "request": {"geo_ids": ["2276"], "worldwide": False, "language_id": "1001", "network": "google"}, "retrieved_at": "now", "truncated": False, "returned_months": ["2025-12", "2026-02"], "results": [kw.normalize(self.result(text="=Übersicht"), "keyword_metrics")]}
        import csv
        rows = list(csv.DictReader(io.StringIO(kw.csv_text(data))))
        self.assertEqual(rows[0]["keyword"], "'=Übersicht")
        self.assertEqual(rows[0]["high_top_of_page_bid"], "")
        self.assertEqual(rows[0]["2026-02"], "0")
        self.assertEqual(rows[0]["currency_code"], "EUR")
        self.assertEqual(rows[0]["average_cpc"], "")
        idea = kw.normalize(self.result("idea", "\t=cmd"), "keyword_idea_metrics")
        idea["concepts"] = [{"name": "Acme", "group": "Brands", "group_type": "BRAND"}, {"name": "x", "group": "", "group_type": None}]
        carriage = kw.normalize(self.result("idea", "\rnote"), "keyword_idea_metrics")
        rows = list(csv.DictReader(io.StringIO(kw.csv_text({**data, "results": [idea, carriage]}))))
        self.assertEqual(rows[0]["keyword"], "'\t=cmd")
        self.assertEqual(rows[0]["concepts"], "BRAND:Acme;x")
        self.assertEqual(rows[1]["keyword"], "'\rnote")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "out.json"
            with patch.object(kw, "load_client"), patch.object(kw, "execute", return_value={**data, "results": [*data["results"], idea]}), contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(kw.main(["metrics", "--customer-id", "1234567890", "--keyword", "x", "--geo-id", "2276", "--language-id", "1001", "--output", str(path)]), 0)
            self.assertEqual(json.loads(path.read_text())["results"][0]["keyword"], "=Übersicht")
            lines = stdout.getvalue().splitlines()
            self.assertTrue(lines[0].startswith("command=metrics\tmarket=2276\tlanguage=1001"))
            self.assertIn("rows=2", lines[0])
            self.assertIn(str(path), lines[0])
            self.assertEqual(lines[1].split("\t")[0], "keyword")
            self.assertEqual(lines[2].split("\t")[:3], ["=Übersicht", "0", "LOW"])
            self.assertEqual(lines[3].split("\t")[-1], "BRAND:Acme")
            self.assertEqual(len(lines), 4)
        data["results"] = []
        self.assertEqual(len(kw.csv_text(data).splitlines()), 1)

    def test_doctor_distinguishes_account_from_planning(self):
        with patch.object(kw, "account", return_value={"test_account": False, "currency_code": "EUR"}):
            data = kw.execute(self.client, self.calls, self.args("doctor"))
            self.assertEqual(data["planning_access"], "not_checked")
            self.service.generate_keyword_historical_metrics.assert_not_called()
            self.service.generate_keyword_historical_metrics.return_value = self.sdk.get_type("GenerateKeywordHistoricalMetricsResponse")
            data = kw.execute(self.client, self.calls, self.args("doctor", "--check-planning", "--keyword", "seed", "--geo-id", "2276", "--language-id", "1001"))
            self.assertEqual(data["planning_access"], "verified")
            self.assertEqual(data["unmatched_keywords"], ["seed"])

    def test_real_sdk_services_expose_expected_methods(self):
        for service, method in [("KeywordPlanIdeaService", "generate_keyword_ideas"), ("KeywordPlanIdeaService", "generate_keyword_historical_metrics"), ("GeoTargetConstantService", "suggest_geo_target_constants"), ("GoogleAdsService", "search_stream")]:
            self.assertTrue(callable(getattr(self.sdk.get_service(service), method)))

    def test_market_lookups_and_account(self):
        response = self.sdk.get_type("SuggestGeoTargetConstantsResponse")
        suggestion = self.sdk.get_type("GeoTargetConstantSuggestion")
        geo = suggestion.geo_target_constant
        geo.id, geo.name, geo.canonical_name = 2276, "Germany", "Germany"
        geo.country_code, geo.target_type = "DE", "Country"
        geo.status = self.sdk.enums.GeoTargetConstantStatusEnum.ENABLED
        response.geo_target_constant_suggestions.append(suggestion)
        self.service.suggest_geo_target_constants.return_value = response
        data = kw.execute(self.client, self.calls, self.args("locations", "--name", "Germany", "--country-code", "de"))
        self.assertEqual(data["results"][0]["id"], "2276")
        self.assertEqual(data["results"][0]["status"], "ENABLED")
        request = self.service.suggest_geo_target_constants.call_args.kwargs["request"]
        self.assertEqual(request.country_code, "DE")
        batch = self.sdk.get_type("SearchGoogleAdsStreamResponse")
        row = self.sdk.get_type("GoogleAdsRow")
        row.language_constant.id = 1001
        row.language_constant.code, row.language_constant.name = "de", "German"
        row.language_constant.targetable = True
        batch.results.append(row)
        self.service.search_stream.return_value = [batch]
        data = kw.execute(self.client, self.calls, self.args("languages"))
        self.assertEqual(data["results"], [{"id": "1001", "code": "de", "name": "German", "targetable": True}])
        batch = self.sdk.get_type("SearchGoogleAdsStreamResponse")
        row = self.sdk.get_type("GoogleAdsRow")
        row.customer.id, row.customer.currency_code = 1234567890, "EUR"
        batch.results.append(row)
        self.service.search_stream.return_value = [batch]
        self.assertEqual(kw.account(self.client, self.calls, "1234567890"), {"customer_id": "1234567890", "currency_code": "EUR", "test_account": False})


if __name__ == "__main__":
    unittest.main()
