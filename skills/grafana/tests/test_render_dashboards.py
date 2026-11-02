import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "render_dashboards.py"
spec = importlib.util.spec_from_file_location("render_dashboards", SCRIPT)
render_dashboards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_dashboards)


def expressions(dashboard):
    return [target["expr"] for panel in dashboard["panels"] for target in panel.get("targets", [])]


def overlaps(panels):
    boxes = [p["gridPos"] for p in panels]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                    and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]):
                return a, b
    return None


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.apps = ["checkout-api", "notes-api", "sync.worker"]
        self.dashboards = render_dashboards.render(
            self.apps, ["production", "staging"], datasource_uid="grafanacloud-prom")
        self.overview = self.dashboards["app-overview.json"]
        self.portfolio = self.dashboards["portfolio.json"]

    def test_overview_variables_follow_the_inventory(self):
        variables = {v["name"]: v for v in self.overview["templating"]["list"]}
        self.assertEqual(list(variables), ["prometheus", "environment", "app"])
        self.assertEqual(variables["app"]["query"], "checkout-api,notes-api,sync.worker")
        self.assertEqual(variables["prometheus"]["current"]["value"], "grafanacloud-prom")

    def test_portfolio_keeps_a_row_per_app_without_app_variable(self):
        rows = [p["title"] for p in self.portfolio["panels"] if p["type"] == "row"]
        self.assertEqual(rows, self.apps)
        names = [v["name"] for v in self.portfolio["templating"]["list"]]
        self.assertEqual(names, ["prometheus", "environment"])
        stats = [p for p in self.portfolio["panels"] if p["type"] == "stat"]
        self.assertEqual(len(stats), 5 * len(self.apps))

    def test_portfolio_queries_bind_each_app(self):
        text = json.dumps(self.portfolio)
        self.assertNotIn("$app", text)
        self.assertNotIn("${app}", text)
        for app in self.apps:
            self.assertIn(f'app=\\"{app}\\"', text)

    def test_portfolio_links_keep_time_and_variables(self):
        stat = next(p for p in self.portfolio["panels"] if p["type"] == "stat")
        url = stat["links"][0]["url"]
        self.assertEqual(
            url, "/d/solo-apps-overview?var-app=checkout-api&${__url_time_range}&${__all_variables}")

    def test_layout_and_ids(self):
        for dashboard in self.dashboards.values():
            ids = [p["id"] for p in dashboard["panels"]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertIsNone(overlaps(dashboard["panels"]))
            self.assertTrue(all(p["gridPos"]["x"] + p["gridPos"]["w"] <= 24 for p in dashboard["panels"]))

    def test_ratios_aggregate_counters_before_dividing(self):
        for expr in expressions(self.overview):
            if " / " in expr:
                self.assertTrue(expr.startswith("100 * sum"), expr)
            self.assertNotIn("avg(", expr)
            self.assertNotIn("or vector(0)", expr)

    def test_native_histogram_queries(self):
        native = render_dashboards.render(["a"], ["production"], histogram="native")
        quantiles = [e for d in native.values() for e in expressions(d) if "histogram_quantile" in e]
        self.assertTrue(quantiles)
        for expr in quantiles:
            self.assertNotIn("_bucket", expr)
            self.assertNotRegex(expr, r"\ble\b")

    def test_template_is_unchanged_by_rendering(self):
        before = render_dashboards.TEMPLATE.read_text()
        render_dashboards.render(["a"], ["production"], histogram="native")
        self.assertEqual(before, render_dashboards.TEMPLATE.read_text())


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_writes_files_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = self.run_cli("--apps", "a", "b", "--output-dir", tmp)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["app-overview.json", "portfolio.json"])
            second = self.run_cli("--apps", "a", "--output-dir", tmp)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("--overwrite", second.stderr)
            third = self.run_cli("--apps", "a", "--output-dir", tmp, "--overwrite")
            self.assertEqual(third.returncode, 0, third.stderr)

    def test_rejects_names_that_would_break_promql_or_uids(self):
        with tempfile.TemporaryDirectory() as tmp:
            for args in (["--apps", 'bad"app'], ["--apps", "a,b"],
                         ["--apps", "a", "--datasource-uid", "has.dot"],
                         ["--apps", "a", "--uid-prefix", "x" * 27]):
                result = self.run_cli(*args, "--output-dir", tmp)
                self.assertEqual(result.returncode, 2, args)


if __name__ == "__main__":
    unittest.main()
