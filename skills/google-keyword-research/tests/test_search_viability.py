"""Offline decisions using saved, explicitly scoped evidence."""
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "search_viability.py"
spec = importlib.util.spec_from_file_location("search_viability", SCRIPT)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
# The API script imports google.ads lazily, so plan validation runs without the SDK.
KEYWORDS = SCRIPT.with_name("google_keywords.py")
spec = importlib.util.spec_from_file_location("viability_google_keywords", KEYWORDS)
kw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kw)
START = date.today() + timedelta(days=2)
END = START + timedelta(days=13)


def brief():
    return {
        "offer": {"name": "Scheduling", "price": "100", "billing_basis": "first monthly payment", "conversion_action": "purchase",
                  "conversion_type": "purchase", "landing_page_url": "https://example.com/buy",
                  "landing_page_live": {"verified": True, "evidence": "Page inspected"}},
        "market": {"currency_code": "EUR", "geo_ids": ["2276"], "language_id": "1001", "network": "google"},
        "test": {"start_date": str(START), "end_date": str(END), "daily_budget": "5", "total_budget": "70"},
        "profiles": [{"id": "buyers", "job": "Buy scheduling", "why_pay": "Save paid admin time", "disqualifier": "Students",
                      "search_stage": "ready_to_buy", "economics": {"first_order_revenue": "100", "variable_costs": "20",
                       "billing_basis": "first monthly payment", "repeat_probability": "0", "page_type": "cold_saas"},
                      "daily_budget": "5", "historical_file": "metrics.json", "forecast_file": "forecast.json",
                      "keywords": [{"keyword": "scheduling software", "match_type": "EXACT", "brand": False, "commercial_intent": True}],
                      "negatives": [{"keyword": "jobs", "match_type": "PHRASE", "scope": "campaign", "reason": "Hiring intent"}],
                      "negative_review": {"verified": True, "evidence": "Disqualifiers and positive conflicts reviewed"},
                      "readiness": {"landing_page_match": {"verified": True, "evidence": "Page sells scheduling"},
                                    "tracking": {"verified": True, "evidence": "Purchase event verified on successful payment"}}}],
        "campaign": {"profile_ids": ["buyers"], "forecast_file": "forecast.json"}}


def history():
    return {"command": "metrics", "retrieved_at": "2026-12-05T00:00:00Z", "account": {"currency_code": "EUR"},
            "request": {"geo_ids": ["2276"], "language_id": "1001", "network": "google"},
            "results": [{"keyword": "scheduling software", "close_variants": ["schedule software"], "avg_monthly_searches": 500,
                         "low_top_of_page_bid": "0.25", "high_top_of_page_bid": "0.50", "monthly_search_volumes": []}]}


def forecast():
    return {"command": "forecast", "account": {"currency_code": "EUR"}, "metrics_basis": "period_total", "period_days": 14,
            "request": {"geo_ids": ["2276"], "language_id": "1001", "currency_code": "EUR", "daily_budget": "5", "max_cpc": "0.72",
                        "bidding_strategy": "manual_cpc", "start_date": str(START), "end_date": str(END),
                        "ad_groups": [{"id": "buyers", "keywords": [{"text": "scheduling software", "match_type": "EXACT"}]}]},
            "results": {"clicks": 200, "cost": "60", "average_cpc": "0.3"}}


class ViabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.brief, self.history, self.forecast = brief(), history(), forecast()

    def evaluate(self):
        for filename, data in (("metrics.json", self.history), ("forecast.json", self.forecast)):
            (self.base / filename).write_text(json.dumps(data))
        return v.run(self.brief, "evaluate", self.base)

    def test_purchase_ceilings_and_default_sources(self):
        result = v.run(self.brief, "economics", self.base)["profiles"][0]
        self.assertEqual(result["max_cac"], Decimal("24"))
        self.assertEqual(result["max_cpa"], Decimal("24"))
        self.assertEqual(result["max_cpc"], Decimal("0.72"))
        self.assertEqual(result["assumptions"]["acquisition_share"]["source"], "default")
        self.assertEqual(result["status"], "READY")

    def test_lead_and_repeat_contribution(self):
        self.brief["offer"]["conversion_type"] = "trial"
        econ = self.brief["profiles"][0]["economics"]
        econ.update(repeat_probability="0.5", repeat_contribution="100")
        result = v.run(self.brief, "economics", self.base)["profiles"][0]
        self.assertEqual(result["contribution_90_days"], Decimal("130"))
        self.assertEqual(result["max_cac"], Decimal("39"))
        self.assertEqual(result["max_cpa"], Decimal("7.8"))
        self.assertEqual(result["max_cpc"], Decimal("0.234"))
        econ["repeat_contribution"] = "1000"
        self.assertEqual(v.run(self.brief, "economics", self.base)["profiles"][0]["max_cac"], Decimal("80"))

    def test_unknown_costs_repeat_and_billing_remain_incomplete(self):
        for key in ("variable_costs", "repeat_probability", "billing_basis"):
            with self.subTest(key=key):
                plan = brief()
                del plan["profiles"][0]["economics"][key]
                result = v.run(plan, "economics", self.base)["profiles"][0]
                self.assertEqual(result["status"], "INCOMPLETE")
        self.brief["profiles"][0]["economics"]["billing_basis"] = "lifetime"
        self.assertEqual(v.run(self.brief, "economics", self.base)["profiles"][0]["status"], "INCOMPLETE")

    def test_zero_negative_contribution_and_rates(self):
        for costs in ("100", "120"):
            self.brief["profiles"][0]["economics"]["variable_costs"] = costs
            self.assertEqual(v.run(self.brief, "economics", self.base)["profiles"][0]["status"], "NO_GO")
        for value in ("NaN", "Infinity", "-0.1", "1.1", True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                v.number(value, "rate", rate=True)

    def test_go_uses_budget_limited_clicks_and_preserves_evidence(self):
        result = self.evaluate()
        row = result["profiles"][0]
        self.assertEqual(row["status"], "GO")
        self.assertEqual(row["purchasable_clicks"], Decimal("140"))
        self.assertEqual(row["stress_spend"], Decimal("70"))
        self.assertEqual(row["expected_conversions"], Decimal("4.2"))
        self.assertEqual(result["campaign"]["status"], "GO")
        self.assertEqual(len(result["evidence"]), 2)
        self.assertEqual(json.loads(v.json_text(result))["inputs"], self.brief)

    def test_click_threshold_is_inclusive_and_zero_is_known(self):
        for clicks, expected in ((100, "GO"), (99, "NO_GO"), (0, "NO_GO"), (None, "INCOMPLETE")):
            self.forecast["results"]["clicks"] = clicks
            with self.subTest(clicks=clicks):
                row = self.evaluate()["profiles"][0]
                self.assertEqual(row["status"], expected)
                if clicks == 0:
                    self.assertIsNone(row["implied_cpa"])

    def test_cpa_equality_is_not_under_ceiling(self):
        self.history["results"][0]["high_top_of_page_bid"] = "0.72"
        result = self.evaluate()
        row = result["profiles"][0]
        self.assertEqual(result["keywords"][0]["decision"], "park")
        self.assertFalse(row["gates"]["surviving_keywords"]["passed"])
        self.assertEqual(row["status"], "NO_GO")
        self.history["results"][0]["high_top_of_page_bid"] = "0.719999"
        self.assertEqual(self.evaluate()["keywords"][0]["decision"], "keep")

    def test_daily_capacity_boundary(self):
        self.brief["profiles"][0]["daily_budget"] = "4.99"
        self.forecast["request"]["daily_budget"] = "4.99"
        row = self.evaluate()["profiles"][0]
        self.assertFalse(row["gates"]["daily_capacity"]["passed"])

    def test_unknown_tracking_and_missing_forecast_do_not_pass(self):
        del self.brief["profiles"][0]["readiness"]["tracking"]["evidence"]
        self.assertEqual(self.evaluate()["profiles"][0]["status"], "INCOMPLETE")
        self.brief = brief()
        del self.brief["profiles"][0]["forecast_file"]
        self.assertEqual(self.evaluate()["profiles"][0]["status"], "INCOMPLETE")

    def test_unknown_economics_or_bids_do_not_become_no_go(self):
        del self.brief["profiles"][0]["economics"]["variable_costs"]
        self.assertEqual(self.evaluate()["profiles"][0]["status"], "INCOMPLETE")
        self.brief = brief()
        self.history["results"][0]["high_top_of_page_bid"] = None
        self.assertEqual(self.evaluate()["profiles"][0]["status"], "INCOMPLETE")

    def test_bid_cap_rounds_down_and_expired_window_is_incomplete(self):
        self.assertEqual(v.bid_cap(Decimal("0.1234569")), Decimal("0.123456"))
        self.brief["test"]["start_date"] = str(date.today() - timedelta(days=15))
        self.brief["test"]["end_date"] = str(date.today() - timedelta(days=2))
        self.forecast["request"]["start_date"] = self.brief["test"]["start_date"]
        self.forecast["request"]["end_date"] = self.brief["test"]["end_date"]
        self.assertEqual(self.evaluate()["profiles"][0]["status"], "INCOMPLETE")

    def test_forecast_must_match_every_scenario_dimension(self):
        changes = {"max_cpc": "0.8", "daily_budget": "10", "language_id": "1000", "geo_ids": ["2840"],
                   "start_date": str(START + timedelta(days=1)), "end_date": str(END + timedelta(days=1)), "ad_groups": []}
        for key, value in changes.items():
            with self.subTest(key=key):
                self.forecast = forecast()
                self.forecast["request"][key] = value
                self.assertIsNone(self.evaluate()["profiles"][0]["gates"]["forecast"]["passed"])
        self.forecast = forecast()
        self.forecast["metrics_basis"] = "daily"
        self.assertIsNone(self.evaluate()["profiles"][0]["gates"]["forecast"]["passed"])

    def test_history_currency_and_market_mismatch_rejected(self):
        self.history["account"]["currency_code"] = "USD"
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_groups_never_summed_and_ambiguous_evidence_unknown(self):
        self.brief["profiles"][0]["keywords"].append({"keyword": "schedule software", "match_type": "PHRASE", "brand": False, "commercial_intent": True})
        result = self.evaluate()
        self.assertEqual([k["historical_group"] for k in result["keywords"]], [0, 0])
        self.assertNotIn("total_searches", result)
        self.history["results"].append(copy.deepcopy(self.history["results"][0]))
        result = self.evaluate()
        self.assertTrue(all(k["high_top_of_page_bid"] is None for k in result["keywords"]))

    def test_missing_bid_can_only_be_resolved_with_explicit_assumptions(self):
        self.history["results"][0]["high_top_of_page_bid"] = None
        profile = self.brief["profiles"][0]
        profile["keywords"][0].update(decision="keep", override_reason="Separate measured CPC evidence")
        row = self.evaluate()["profiles"][0]
        self.assertEqual(row["status"], "INCOMPLETE")
        profile.update(stress_cpc="0.50", stress_cpc_reason="Measured comparable traffic; provisional assumption")
        self.assertEqual(self.evaluate()["profiles"][0]["status"], "GO")

    def test_low_volume_is_flag_not_automatic_rejection(self):
        self.history["results"][0]["avg_monthly_searches"] = 20
        result = self.evaluate()
        self.assertTrue(result["keywords"][0]["low_volume_flag"])
        self.assertEqual(result["profiles"][0]["status"], "GO")

    def test_brand_and_informational_keywords_cannot_be_forced_into_go(self):
        for field, value in (("brand", True), ("commercial_intent", False)):
            self.brief = brief()
            self.brief["profiles"][0]["keywords"][0].update({field: value, "decision": "keep", "override_reason": "Try it"})
            with self.assertRaises(ValueError):
                self.evaluate()

    def test_combined_forecast_not_sum_of_profile_scenarios(self):
        second = copy.deepcopy(self.brief["profiles"][0])
        second["id"] = "second"
        self.brief["profiles"].append(second)
        self.brief["campaign"]["profile_ids"].append("second")
        result = self.evaluate()
        self.assertFalse(result["campaign"]["gates"]["budget_allocations"]["passed"])
        self.assertIsNone(result["campaign"]["gates"]["forecast"]["passed"])

    def test_trend_requires_consecutive_complete_months_and_nonzero_base(self):
        months = [{"month": f"2026-{m:02d}", "searches": 100 + 10 * (m - 8)} for m in range(8, 13)]
        result = v.trend(months, date(2026, 12, 5))
        self.assertEqual(result, {"from": "2026-08", "to": "2026-11", "percent": Decimal("30")})
        self.assertIsNone(v.trend(months[1:], date(2026, 12, 5))["percent"])
        months[0]["searches"] = 0
        self.assertIsNone(v.trend(months, date(2026, 12, 5))["percent"])
        months[0]["searches"] = 100
        months[1]["searches"] = None
        self.assertIsNone(v.trend(months, date(2026, 12, 5))["percent"])

    def test_threshold_overrides_need_reason(self):
        self.brief["test"]["thresholds"] = {"min_clicks": 50}
        with self.assertRaises(ValueError):
            self.evaluate()
        self.brief["test"]["override_reason"] = "Small pilot"
        self.assertEqual(self.evaluate()["thresholds"]["min_clicks"], 50)

    def cli(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            try:
                code = v.main(list(argv))
            except SystemExit as exit:
                code = exit.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_forecast_plans_validate_and_round_trip(self):
        self.evaluate()
        del self.brief["profiles"][0]["forecast_file"], self.brief["campaign"]["forecast_file"]
        path, plans = self.base / "plan.json", self.base / "plans"
        path.write_text(json.dumps(self.brief))
        plans.mkdir()
        code, stdout, stderr = self.cli("evaluate", "--input", str(path), "--output", str(self.base / "out.json"), "--forecast-plans", str(plans))
        self.assertEqual((code, stderr), (0, ""))
        written = json.loads((self.base / "out.json").read_text())["forecast_plans"]
        self.assertEqual([(e["id"], e["skipped"]) for e in written], [("buyers", None), ("campaign", None)])
        self.assertIn("forecast_plan\tbuyers\t", stdout)
        self.assertIn("buyers\tINCOMPLETE\t0.7200\t\tforecast", stdout)
        for name in ("buyers", "campaign"):
            plan = json.loads((plans / f"{name}.forecast-plan.json").read_text())
            self.assertEqual(kw.validate_forecast_plan(plan), plan)
            self.assertEqual(plan["max_cpc"], "0.720000")
            self.assertEqual(plan["bidding_strategy"], "manual_cpc")
        # An export whose request is the generated plan passes the forecast gate.
        self.forecast["request"] = json.loads((plans / "buyers.forecast-plan.json").read_text())
        self.brief = brief()
        result = self.evaluate()
        self.assertTrue(result["profiles"][0]["gates"]["forecast"]["passed"])
        self.assertEqual(result["campaign"]["status"], "GO")

    def test_forecast_plans_skip_reasons_and_unsafe_ids(self):
        self.history["results"][0]["high_top_of_page_bid"] = "0.9"
        self.evaluate()
        path, plans = self.base / "plan.json", self.base / "plans"
        path.write_text(json.dumps(self.brief))
        plans.mkdir()
        code, _, _ = self.cli("evaluate", "--input", str(path), "--output", str(self.base / "out.json"), "--forecast-plans", str(plans))
        self.assertEqual(code, 0)
        skipped = {e["id"]: e["skipped"] for e in json.loads((self.base / "out.json").read_text())["forecast_plans"]}
        self.assertEqual(skipped, {"buyers": "no kept keywords", "campaign": "no kept keywords"})
        self.assertEqual(list(plans.iterdir()), [])
        self.history = history()
        self.brief["profiles"][0]["id"] = "../buyers"
        self.brief["campaign"]["profile_ids"] = ["../buyers"]
        self.evaluate()
        path.write_text(json.dumps(self.brief))
        code, _, stderr = self.cli("evaluate", "--input", str(path), "--forecast-plans", str(plans))
        self.assertEqual(code, 1)
        self.assertIn("file name", stderr)
        self.assertEqual(self.cli("economics", "--input", str(path), "--forecast-plans", str(plans))[0], 2)

    def test_forecast_mismatch_names_fields(self):
        self.forecast["request"]["max_cpc"] = "0.8"
        self.forecast["request"]["ad_groups"][0]["keywords"][0]["match_type"] = "PHRASE"
        reason = self.evaluate()["profiles"][0]["gates"]["forecast"]["reason"]
        self.assertTrue(reason.startswith("Forecast mismatch: max_cpc, ad_groups;"), reason)
        self.assertIn("buyers.forecast-plan.json", reason)
        self.forecast = forecast()
        self.brief["test"]["bidding_strategy"] = "maximize_clicks"
        self.assertIn("bidding_strategy", self.evaluate()["profiles"][0]["gates"]["forecast"]["reason"])
        self.forecast["request"]["bidding_strategy"] = "maximize_clicks"
        self.assertTrue(self.evaluate()["profiles"][0]["gates"]["forecast"]["passed"])
        self.brief["test"]["bidding_strategy"] = "target_cpa"
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_scaffold_hints_brand_and_feeds_evaluate(self):
        self.history["command"] = "ideas"
        self.history["results"][0].update(average_cpc="0.40", concepts=[{"name": "Software", "group": "Product", "group_type": "NON_BRAND"}])
        self.history["results"].append({"keyword": "calendly pricing", "close_variants": [], "avg_monthly_searches": 90, "high_top_of_page_bid": "0.60",
                                        "monthly_search_volumes": [], "concepts": [{"name": "Calendly", "group": "Brands", "group_type": "OTHER_BRANDS"}]})
        self.evaluate()
        path = self.base / "plan.json"
        path.write_text(json.dumps(self.brief))
        code, stdout, _ = self.cli("scaffold", "--historical", str(self.base / "metrics.json"), "--profile-id", "buyers",
                                   "--input", str(path), "--output", str(self.base / "scaffold.json"))
        self.assertEqual(code, 0, _)
        self.assertIn("keywords=2\tbrand_hints=1", stdout)
        scaffold = json.loads((self.base / "scaffold.json").read_text())
        self.assertEqual(scaffold["historical_file"], "metrics.json")
        self.assertEqual([(k["keyword"], k["match_type"], k["brand"], k["commercial_intent"]) for k in scaffold["keywords"]],
                         [("scheduling software", "PHRASE", None, None), ("calendly pricing", "PHRASE", True, None)])
        self.assertEqual(scaffold["keywords"][0]["average_cpc"], "0.40")
        scaffold["keywords"][0].update(commercial_intent=True, brand=False)
        self.brief["profiles"][0]["keywords"] = scaffold["keywords"]
        self.forecast["request"]["ad_groups"][0]["keywords"][0]["match_type"] = "PHRASE"
        result = self.evaluate()
        self.assertEqual([k["decision"] for k in result["keywords"]], ["keep", "exclude"])
        self.assertEqual(result["keywords"][0]["average_cpc"], Decimal("0.40"))
        self.assertEqual(result["profiles"][0]["status"], "GO")
        self.history["request"]["language_id"] = "1000"
        (self.base / "metrics.json").write_text(json.dumps(self.history))
        self.assertEqual(self.cli("scaffold", "--historical", str(self.base / "metrics.json"), "--profile-id", "buyers", "--input", str(path))[0], 1)
        self.assertEqual(self.cli("scaffold", "--historical", str(self.base / "metrics.json"))[0], 2)

    def test_match_status_cases(self):
        keywords = self.brief["profiles"][0]["keywords"]
        keywords.append({"keyword": "missing term", "match_type": "EXACT", "brand": False, "commercial_intent": True})
        result = self.evaluate()
        self.assertEqual([(k["match_status"], k["decision"]) for k in result["keywords"]], [("matched", "keep"), ("unmatched", "park")])
        self.assertIn("No historical match", result["keywords"][1]["reason"])
        self.history["results"].append(copy.deepcopy(self.history["results"][0]))
        row = self.evaluate()["keywords"][0]
        self.assertEqual(row["match_status"], "ambiguous")
        self.assertEqual(row["reason"], "Ambiguous historical match; split or override")
        del self.brief["profiles"][0]["historical_file"]
        self.assertEqual({k["match_status"] for k in self.evaluate()["keywords"]}, {"no_history"})

    def test_market_time_zone_sets_today(self):
        # Kiritimati (UTC+14) is always one or two calendar days ahead of Pago Pago (UTC-11).
        start = datetime.now(ZoneInfo("Pacific/Pago_Pago")).date() + timedelta(days=1)
        self.brief["test"].update(start_date=str(start), end_date=str(start + timedelta(days=13)))
        self.brief["market"]["time_zone"] = "Pacific/Pago_Pago"
        self.assertEqual(v.today(self.brief), datetime.now(ZoneInfo("Pacific/Pago_Pago")).date())
        self.assertTrue(self.evaluate()["profiles"][0]["gates"]["test_dates"]["passed"])
        self.brief["market"]["time_zone"] = "Pacific/Kiritimati"
        self.assertIsNone(self.evaluate()["profiles"][0]["gates"]["test_dates"]["passed"])
        self.brief["market"]["time_zone"] = "Mars/Olympus"
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_cli_exports_protect_inputs_and_escape_formulas(self):
        self.evaluate()
        path = self.base / "plan.json"
        path.write_text(json.dumps(self.brief))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(v.main(["evaluate", "--input", str(path), "--output", str(self.base / "out.json"), "--csv", str(self.base / "decisions.csv")]), 0)
            self.assertEqual(v.main(["evaluate", "--input", str(path), "--output", str(self.base / "forecast.json")]), 1)
        self.assertEqual(json.loads((self.base / "forecast.json").read_text()), self.forecast)
        self.assertIn("'=formula", v.csv_text([{"keyword": "=formula"}]))
        self.assertIn("'\t=formula", v.csv_text([{"keyword": "\t=formula"}]))
        self.assertIn("'\rnote", v.csv_text([{"keyword": "\rnote"}]))
        self.assertTrue((self.base / "decisions.csv").exists())


if __name__ == "__main__":
    unittest.main()
