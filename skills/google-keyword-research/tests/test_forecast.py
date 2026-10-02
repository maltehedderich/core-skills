"""v25 forecast requests and period-total output contract."""
import copy
import contextlib
import csv
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from google.ads.googleads.client import GoogleAdsClient
from google.auth.credentials import AnonymousCredentials
from google.api_core import exceptions

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "google_keywords.py"
spec = importlib.util.spec_from_file_location("forecast_keywords", SCRIPT)
kw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kw)


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.sdk = GoogleAdsClient(credentials=AnonymousCredentials(), use_proto_plus=True, version="v25")
        self.service = Mock()
        self.client = SimpleNamespace(get_type=self.sdk.get_type, enums=self.sdk.enums, get_service=Mock(return_value=self.service))
        batch = self.sdk.get_type("SearchGoogleAdsStreamResponse")
        row = self.sdk.get_type("GoogleAdsRow")
        row.customer.time_zone = "Europe/Berlin"
        batch.results.append(row)
        self.service.search_stream.return_value = [batch]
        start = datetime.now(ZoneInfo("Europe/Berlin")).date() + timedelta(days=2)
        self.plan = {"currency_code": "EUR", "geo_ids": ["2276"], "language_id": "1001", "start_date": str(start),
                     "end_date": str(start + timedelta(days=13)), "daily_budget": "12.34", "max_cpc": "0.72", "bidding_strategy": "manual_cpc",
                     "ad_groups": [{"id": "buyers", "keywords": [{"text": "software", "match_type": "EXACT"}, {"text": "buy software", "match_type": "PHRASE"}]}]}
        self.response = self.sdk.get_type("GenerateKeywordForecastMetricsResponse")
        self.response.campaign_forecast_metrics.clicks = 140
        self.response.campaign_forecast_metrics.cost_micros = 70_000_000
        self.response.campaign_forecast_metrics.average_cpc_micros = 500_000
        self.service.generate_keyword_forecast_metrics.return_value = self.response
        self.calls = kw.Calls(sleep=lambda _: None)

    def forecast(self):
        return kw.forecast(self.client, self.calls, SimpleNamespace(plan=kw.validate_forecast_plan(self.plan), customer_id="1234567890"), {"currency_code": "EUR"})

    def test_manual_request_and_period_totals(self):
        data = self.forecast()
        request = self.service.generate_keyword_forecast_metrics.call_args.kwargs["request"]
        self.assertEqual(request.customer_id, "1234567890")
        self.assertEqual(list(request.campaign.geo_target_constants), ["geoTargetConstants/2276"])
        self.assertEqual(request.campaign.bidding_strategy.manual_cpc_bidding_strategy.daily_budget_micros, 12340000)
        self.assertEqual(request.campaign.bidding_strategy.manual_cpc_bidding_strategy.max_cpc_bid_micros, 720000)
        self.assertEqual([k.match_type.name for k in request.campaign.ad_groups[0].keywords], ["EXACT", "PHRASE"])
        self.assertEqual(data["results"]["clicks"], 140)
        self.assertEqual(data["results"]["daily_clicks"], "10.0")
        self.assertEqual(data["results"]["cost"], "70")
        self.assertEqual(data["results"]["daily_cost"], "5")
        self.assertEqual(data["period_days"], 14)
        self.assertEqual(data["metrics_basis"], "period_total")
        self.assertIn("not modeled", data["warnings"][0])

    def test_maximize_clicks_budget_and_ceiling(self):
        self.plan["bidding_strategy"] = "maximize_clicks"
        self.forecast()
        request = self.service.generate_keyword_forecast_metrics.call_args.kwargs["request"]
        strategy = request.campaign.bidding_strategy.maximize_clicks_bidding_strategy
        self.assertEqual(strategy.daily_target_spend_micros, 12340000)
        self.assertEqual(strategy.max_cpc_bid_ceiling_micros, 720000)

    def test_zero_and_missing_are_different(self):
        self.response = self.sdk.get_type("GenerateKeywordForecastMetricsResponse")
        self.service.generate_keyword_forecast_metrics.return_value = self.response
        self.assertIsNone(self.forecast()["results"]["clicks"])
        self.response.campaign_forecast_metrics.clicks = 0
        self.response.campaign_forecast_metrics.cost_micros = 0
        data = self.forecast()
        self.assertEqual(data["results"]["clicks"], 0)
        self.assertEqual(data["results"]["cost"], "0")
        self.assertIsNone(data["results"]["average_cpc"])

    def test_currency_and_dates_fail_before_forecast_call(self):
        for field, value in (("currency_code", "USD"), ("start_date", "2000-01-01"), ("end_date", "2099-01-01")):
            original = copy.deepcopy(self.plan)
            self.plan[field] = value
            with self.subTest(field=field), self.assertRaises(kw.UserError):
                self.forecast()
            self.plan = original
        self.service.generate_keyword_forecast_metrics.assert_not_called()

    def test_unsupported_fields_and_bad_inputs_rejected(self):
        for field, value in (("network", "google"), ("negatives", []), ("daily_budget", "NaN"), ("max_cpc", "0.0000001"), ("geo_ids", ["2276", "2276"]), ("bidding_strategy", "maximize_conversions"), ("ad_groups", [])):
            plan = copy.deepcopy(self.plan)
            plan[field] = value
            with self.subTest(field=field), self.assertRaises(kw.UserError):
                kw.validate_forecast_plan(plan)
        self.plan["ad_groups"][0]["keywords"][0]["match_type"] = "BROAD"
        with self.assertRaises(kw.UserError):
            kw.validate_forecast_plan(self.plan)

    def test_worldwide_is_explicit_and_sdk_method_exists(self):
        self.plan.pop("geo_ids")
        with self.assertRaises(kw.UserError):
            kw.validate_forecast_plan(self.plan)
        self.plan["worldwide"] = True
        self.forecast()
        request = self.service.generate_keyword_forecast_metrics.call_args.kwargs["request"]
        self.assertEqual(list(request.campaign.geo_target_constants), [])
        self.assertTrue(callable(self.sdk.get_service("KeywordPlanIdeaService").generate_keyword_forecast_metrics))

    def test_cli_round_trip_and_failure_preserves_existing_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            plan, output, spreadsheet = base / "plan.json", base / "out.json", base / "out.csv"
            plan.write_text(json.dumps(self.plan))
            argv = ["forecast", "--customer-id", "1234567890", "--plan-file", str(plan), "--output", str(output), "--csv", str(spreadsheet)]
            with patch.object(kw, "load_client", return_value=self.client), patch.object(kw, "account", return_value={"currency_code": "EUR", "test_account": False}):
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(kw.main(argv), 0)
                self.assertTrue(stdout.getvalue().startswith("command=forecast\tmarket=2276"))
                self.assertIn("140", stdout.getvalue().splitlines()[2])
                exported = output.read_text()
                self.assertEqual(json.loads(exported)["request"], self.plan)
                row = list(csv.DictReader(io.StringIO(spreadsheet.read_text())))[0]
                self.assertEqual(row["clicks"], "140.0")
                self.assertEqual(row["daily_clicks"], "10.0")
                self.service.generate_keyword_forecast_metrics.side_effect = exceptions.PermissionDenied("SECRET")
                with contextlib.redirect_stderr(io.StringIO()) as stderr, contextlib.redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(kw.main(argv), 1)
                self.assertEqual(stdout.getvalue(), "")
                self.assertNotIn("SECRET", stderr.getvalue())
                self.assertEqual(output.read_text(), exported)
            args = kw.parser().parse_args(["forecast", "--customer-id", "1234567890", "--plan-file", str(plan), "--output", str(plan)])
            with self.assertRaises(kw.UserError):
                kw.prepare(args)


if __name__ == "__main__":
    unittest.main()
