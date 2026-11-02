# Dashboard creation and delivery

## Default: versioned JSON

Use the bundled Classic JSON model for a portable starting point. Grafana supports JSON import; newer versions also offer V1/V2 resource formats. Keep the format already used by an existing project. A template is useful only after its names, labels, histogram type, and units match ingested data. [JSON models](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/), [importing dashboards](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/import-dashboards/)

From the repository that will version the dashboards, render local files. `SKILL_DIR` is this skill's installed directory; the script finds its template relative to itself.

```sh
uv run "$SKILL_DIR/scripts/render_dashboards.py" \
  --apps checkout-api notes-api sync-worker \
  --environments production \
  --datasource-uid YOUR_HOSTED_PROMETHEUS_UID \
  --output-dir monitoring/grafana
```

This writes `app-overview.json` and `portfolio.json`, without network access. It refuses to overwrite existing output unless passed `--overwrite`. `--histogram native` switches quantile expressions to native histograms. `--uid-prefix` lets separate portfolios coexist. App and environment names are restricted to simple identifiers; adapt the renderer or JSON for an existing contract with other label values. The data source UID is on the data source's settings page and in its URL.

The app dashboard has single-select app/environment variables from an explicit inventory, a selectable Prometheus data source, 15-minute operation/failure/latency summaries, sample age, per-minute operation and latency trends, and per-operation tables. The portfolio contains the same summary panels for each expected app with a detail link. This keeps a nonreporting app visible. The portfolio needs the same metric contract across its apps; customize mixed data-source deployments per row.

The template can also be imported directly, replacing its example app/environment values. It uses a data-source variable, not unresolved `__inputs`, so it can be adapted to UI import, API, or Terraform. A known datasource UID makes the selection deterministic. The generator writes the explicit inventory into both dashboards; rerun it when adding/removing an app and review the diff before replacing customized dashboards.

## Panel semantics

- Operation counts include every outcome; failure counts are the `outcome="failure"` subset. Both use `increase(...[15m])` and are estimates. A live initialized series with no increments shows zero, while absent data shows **No data**.
- Failure percentage uses the same eligible population. A zero denominator maps to **No traffic / undefined**; a missing numerator remains **No data**. Do not hide a missing failure instrument with `or vector(0)`.
- p95 uses a 15-minute histogram window and seconds. No observations produces an undefined quantile; sparse observations are not a robust tail estimate. All-outcome latency can improve during fast failures.
- Sample age reports the newest visible counter sample, not last successful operation or whole-fleet coverage. After Prometheus's lookback/staleness handling expires, it shows **No data**. On intentionally idle serverless apps, distinguish expected silence using platform metrics or an external check.
- Trend panels show operations per minute, which stays readable for sparse traffic where per-second rates round to zero. Their `$__rate_interval` depends on the 1-minute Min step set on each query; see the budget reference.
- The operation tables separate traffic, failures, and p95 so each remains useful when another signal is missing. They use the same operation label and time window.

The default has no green/red health judgment or invented target. Add thresholds only from an agreed expectation and include text. An optional journey check can establish independent availability; backend counters alone cannot.

## Import and inspect

1. Import both generated JSON files into the chosen Grafana folder. Reuse stable UIDs for future updates, after checking for an existing dashboard with the same UID.
2. Select the hosted Prometheus data source and save. Verify a raw series in Explore before diagnosing empty panels as a dashboard issue.
3. Check app/environment selection, the known no-traffic case, a controlled failure, and a missing app. Inspect the layout and portfolio-to-detail links. The links carry the time range (`${__url_time_range}`) and the portfolio's variables, adding the row's app selection.
4. Add useful links to provider logs, existing error tracking, a runbook, and the usage dashboard. Provider URLs and timestamp formats differ; build them from the project's actual resources and verify them. Never insert fake working destinations.
5. Add deployment annotations if the project already emits them or the timing is useful. Avoid a new event pipeline just to fill an annotation row.

For provider-native metrics, build a small dashboard using the data source's real query model and export its JSON. Reuse the same visual hierarchy and null semantics; the included PromQL is not portable to CloudWatch or every Cloud Monitoring query. A shared Grafana dashboard can contain multiple data sources.

## Automation when it helps

| Existing workflow | Choice |
| --- | --- |
| A few dashboards, no IaC | Import JSON in the UI; commit the exported source |
| Repeated dashboard delivery through scripts/CI | Grafana HTTP API with a narrowly scoped service account |
| Grafana already managed in Terraform | Reuse the provider, state, folder, and dashboard resource |

For API work, discover the target Grafana version and current endpoint. Grafana 13 deprecates legacy `/api` routes in favor of `/apis`; legacy routes remain operational for now. New APIs use resource envelopes and concurrency metadata, so do not POST a Classic JSON object to an arbitrary `/apis` endpoint. Use current official documentation and the appropriate envelope. Avoid building a new legacy-only uploader into the application. [HTTP API migration](https://grafana.com/docs/grafana/latest/developer-resources/api-reference/http-api/apis/)

For updates, retrieve the current dashboard, check its UID/folder/version or resource version, review the diff, and preserve unrelated edits. Handle a conflict by rereading and reconciling; do not blindly retry with overwrite. Use a stable UID and stop after successful creation/update. A Grafana service-account token manages dashboards; it is not the OTLP write token. Keep both out of JSON, git, logs, and command-line arguments.

If using Terraform, verify the installed Grafana provider's current dashboard resource and import behavior. Use the JSON file as the dashboard source, stable UIDs, an existing folder, secret-injected credentials, and a reviewed plan. Do not introduce a new state/backend solely for this task or let a plan delete unrelated dashboards. Import existing resources before taking over their management. Filesystem provisioning is primarily for self-hosted Grafana, not access to Grafana Cloud's server filesystem.

## Completion evidence

Local JSON parsing and query inspection establish that artifacts are prepared. They do not establish successful Grafana import, ingestion, or rendered usability. With access, open the dashboard and verify actual values and layout, then report its URL and observed usage. Without access, hand over the import files, identify required datasource/credentials, and state exactly which live checks remain.
