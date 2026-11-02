#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Render an app dashboard and an explicit-inventory portfolio; no network calls."""

import argparse
import copy
import json
import re
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "app-overview.json"
APP_REFERENCE = re.compile(r"\$\{app\}|\$app\b")


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", value):
        raise argparse.ArgumentTypeError(
            "Use 1–63 letters, digits, dots, underscores or hyphens, starting with a letter/digit."
        )
    return value


def grafana_uid(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", value):
        raise argparse.ArgumentTypeError("Grafana UIDs use 1–40 letters, digits, underscores or hyphens.")
    return value


def uid_prefix(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,25}", value):
        raise argparse.ArgumentTypeError("UID prefix must be 1–26 letters, digits, underscores or hyphens.")
    return value


def map_strings(value, transform):
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, list):
        return [map_strings(item, transform) for item in value]
    if isinstance(value, dict):
        return {key: map_strings(item, transform) for key, item in value.items()}
    return value


def custom_variable(name, values):
    return {
        "name": name,
        "label": name.capitalize(),
        "type": "custom",
        "query": ",".join(values),
        "current": {"text": values[0], "value": values[0]},
        "options": [
            {"text": value, "value": value, "selected": i == 0}
            for i, value in enumerate(values)
        ],
        "multi": False,
        "includeAll": False,
        "hide": 0,
    }


def render(apps, environments, datasource_uid=None, prefix="solo-apps", histogram="classic"):
    overview = json.loads(TEMPLATE.read_text())
    overview["uid"] = f"{prefix}-overview"
    overview["title"] = "Application overview"
    datasource = next(v for v in overview["templating"]["list"] if v["type"] == "datasource")
    if datasource_uid:
        datasource["current"] = {"text": datasource_uid, "value": datasource_uid}
    overview["templating"]["list"] = [
        datasource,
        custom_variable("environment", environments),
        custom_variable("app", apps),
    ]
    if histogram == "native":
        def native_query(value):
            if "app_operation_duration_seconds_bucket" not in value:
                return value
            return (value.replace("app_operation_duration_seconds_bucket", "app_operation_duration_seconds")
                    .replace("sum by (le, operation)", "sum by (operation)")
                    .replace("sum by (le)", "sum"))
        overview = map_strings(overview, native_query)

    portfolio = copy.deepcopy(overview)
    portfolio["uid"] = f"{prefix}-portfolio"
    portfolio["title"] = "Application portfolio"
    portfolio["description"] = "Explicit app inventory. No data and undefined ratios are not healthy zeros."
    portfolio["templating"]["list"] = [
        copy.deepcopy(v) for v in overview["templating"]["list"] if v["name"] != "app"
    ]
    portfolio["panels"] = [{
        "id": 1,
        "type": "text",
        "title": "Portfolio coverage",
        "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3},
        "options": {"mode": "markdown", "content": (
            "Each configured app keeps a row even when it stops reporting. Counts are estimated over "
            "15 minutes; no traffic and absent telemetry need different investigations. "
            "Sample age covers the newest visible writer only. Click a summary panel's link for details."
        )},
    }]
    summaries = [panel for panel in overview["panels"] if panel["type"] == "stat"]
    y = 3
    next_id = 2
    for app in apps:
        portfolio["panels"].append({
            "id": next_id, "type": "row", "title": app, "collapsed": False,
            "panels": [], "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
        })
        next_id += 1
        for summary in summaries:
            panel = map_strings(copy.deepcopy(summary), lambda value: APP_REFERENCE.sub(app, value))
            panel["id"] = next_id
            panel["gridPos"]["y"] = y + 1
            panel["links"] = [{
                "title": f"Open {app}",
                "url": f"/d/{overview['uid']}?var-app={app}&${{__url_time_range}}&${{__all_variables}}",
                "targetBlank": False,
            }]
            portfolio["panels"].append(panel)
            next_id += 1
        y += 6
    overview["links"] = [{
        "title": "Application portfolio", "type": "link",
        "url": f"/d/{portfolio['uid']}", "includeVars": True, "keepTime": True,
        "targetBlank": False,
    }]
    return {"app-overview.json": overview, "portfolio.json": portfolio}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apps", nargs="+", type=identifier, required=True)
    parser.add_argument("--environments", nargs="+", type=identifier, default=["production"])
    parser.add_argument("--datasource-uid", type=grafana_uid)
    parser.add_argument("--uid-prefix", type=uid_prefix, default="solo-apps")
    parser.add_argument("--histogram", choices=["classic", "native"], default="classic")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    apps = list(dict.fromkeys(args.apps))
    environments = list(dict.fromkeys(args.environments))
    dashboards = render(apps, environments, args.datasource_uid, args.uid_prefix, args.histogram)
    for name in dashboards:
        destination = args.output_dir / name
        if destination.exists() and not args.overwrite:
            parser.error(f"Output exists: {destination}. Review it before using --overwrite.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, dashboard in dashboards.items():
        destination = args.output_dir / name
        destination.write_text(json.dumps(dashboard, indent=2) + "\n")
        print(destination)


if __name__ == "__main__":
    main()
