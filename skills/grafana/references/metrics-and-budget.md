# Metric contract and usage budget

## Start with user operations

Choose one to three critical operations and write down eligibility, success, failure, and latency boundaries. Examples include completing checkout, saving a document, or syncing data. Exclude health checks and synthetic traffic from business-operation counts, or distinguish them with a bounded operation name. Count each eligible operation once at its defined completion boundary; retries must not accidentally multiply user outcomes. Define whether cancellations and expected validation failures are eligible.

Existing HTTP metrics can provide a service overview, but title a 5xx panel precisely. A 200 response is not proof of business success. Avoid counting a request and its nested business operation together as if they were separate eligible requests. Use separate metrics or non-overlapping scopes when both are needed. [Google SRE monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)

## Bundled dashboard contract

These are **ingested Prometheus names**, not guaranteed SDK instrument names. Map existing names and labels to them in dashboard queries when that avoids duplicate instrumentation.

| Metric | Type / unit | Labels | Meaning |
| --- | --- | --- | --- |
| `app_operations_total` | Cumulative counter | `app`, `environment`, `operation`, `outcome` | Completed eligible operations; `outcome` is `success` or `failure` |
| `app_operation_duration_seconds` | Histogram / seconds | `app`, `environment`, `operation` | Duration of the same eligible operations |

Keep writer identity (`instance`, or the pipeline's equivalent) on both metrics until query-time aggregation. Use stable bounded application/environment names. `operation` is a named critical action or normalized route such as `POST /orders/{id}`, never a raw path. Put method in the operation name only when useful. Start with at most roughly ten operations per app; that is a planning preference, not a product limit.

Initialize both known counter outcomes to zero for every intended operation/writer. This makes zero failures observable; missing failure series remain an instrumentation problem. If the SDK does not export zero-initialized instruments, explicitly test an alternative that preserves the distinction between missing telemetry and a known zero. Do not blanket-fill empty queries with zero.

Use histogram boundaries that reflect the application's latency questions. The classic compatibility template can start with seven finite boundaries in seconds: `0.05, 0.1, 0.25, 0.5, 1, 2.5, 5`, plus `+Inf`. Adjust them for a slow job or a specific latency objective, consistently across writers. Always set boundaries explicitly through a view or the instrument's advisory boundaries: the OTel SDK default has 15 boundaries scaled for milliseconds (`0, 5, 10, …, 10000`), so a seconds-based histogram puts nearly every observation in the first buckets and costs almost twice the series. Seven finite buckets create ten series per label set: eight buckets, sum, and count. Do not multiply the histogram by status, outcome, version, and method unless the split is useful. When fast failures distort latency, add a bounded outcome split or a separate successful-operation histogram, and update the queries and budget.

Prefer native/exponential histograms for new instrumentation when the SDK, exporter, and backend preserve them. The bundled renderer supports `--histogram native`; verify the ingested representation first. A classic histogram has `_bucket{le=...}` series. Native histograms use the base metric in `histogram_quantile`. Do not export both representations by accident. Native histogram sample sizes and billing weights can differ; fewer visible series do not automatically imply proportional savings. [Prometheus histogram guidance](https://prometheus.io/docs/practices/histograms/), [Prometheus instrumentation](https://prometheus.io/docs/practices/instrumentation/)

OTel may append units and counter suffixes during translation. For example, an instrument with duration unit `s` can acquire a `_seconds` suffix. Inspect the stored name instead of guessing or manually adding a duplicate suffix. Apply the bounded metric attributes in instrumentation/views or in a verified collector transform; resource attributes alone may not supply the template's labels.

## Add only useful diagnostics

| Workload / symptom | Small additional signal |
| --- | --- |
| Jobs with a deadline | Durable last-success timestamp and run result; show age against the expected schedule |
| Queued work | Oldest pending age, optionally queue depth and completion rate |
| Work stalls before completing | In-progress count and an external check or deadline signal |
| Connection bottleneck | Pool wait duration/timeouts and in-use versus limit |
| Suspected container exhaustion | Existing provider CPU throttling, memory/limit, or OOM evidence |

A last-success gauge must come from durable state or a periodically queried provider metric. A one-shot job's final sample will go stale; `time() - last_success` is not reliable if the series disappears. Do not add Pushgateway, a scheduler, or permanent compute unless simpler existing state cannot answer the question. Show no-data explicitly and define lateness from the real schedule.

## Budget for the entire portfolio

As checked on 2026-11-02, Grafana advertises **10,000 metric series and 14-day retention** for its free tier. Confirm actual plan, active-series/sample limits, and usage in the stack before rollout; trial/paid plans and newer product bundles differ. Do not turn on a trial or paid feature implicitly. [Free tier](https://grafana.com/products/cloud/free-tier/), [metrics allowance](https://grafana.com/products/cloud/metrics/)

Grafana counts recently reporting series as active (documented window: 20 minutes), so recently terminated writers can overlap with replacements. Export frequency matters too: 15 seconds produces four times the samples of 60 seconds without reducing the series count. Start near 60 seconds. Grafana derives `$__rate_interval` from each query's Min step before the data source's scrape interval, so the bundled queries set a 1-minute Min step (`"interval": "1m"`) and get windows of at least four samples without editing Grafana Cloud's managed data source. Change every query's Min step if you change the export interval. Dashboard refresh frequency is separate; slowing it does not reduce samples already pushed. [Usage calculation](https://grafana.com/docs/grafana-cloud/cost-management-and-billing/understand-usage-cost/metrics/), [DPM guidance](https://grafana.com/blog/data-points-per-minute-in-grafana-cloud-what-you-need-to-know-about-dpm/)

For classic histograms, estimate:

```text
counter series = apps × environments × operations × outcomes × concurrent writers
histogram series = apps × environments × operations × (finite buckets + 3) × concurrent writers
DPM ≈ emitted series × 60 / export interval in seconds
```

Use actual combinations per metric rather than multiplying unrelated dimensions across all metrics. Include independently varying region/worker labels, deployment overlap, rolling instance churn, metadata, optional created-series, SDK runtime metrics, existing integrations, and synthetic-check series. Preserve writer identity to avoid collisions; reduce unnecessary families/dimensions or use a correct stateful aggregation pipeline instead.

Worked planning estimate: five apps, one environment, ten operations each, two writers per app, two counter outcomes, and seven finite histogram buckets yields `5 × 10 × 2 × (2 + 10) = 1,200` series, about 1,200 DPM at 60 seconds. This excludes overhead and churn. A full old/new writer overlap could roughly double it. Five writers instead of two increases the baseline to 3,000. This is an estimate, not a quota guarantee.

For an initially small portfolio, aim for roughly 300–500 baseline series per app and at least 30% total headroom; revise for app count and existing consumption. Both are conservative planning preferences. Allowlisting metric families, limiting operations, and removing unused histogram dimensions usually matter more than lowering the export frequency below one sample per minute.

After rollout, use the built-in **grafanacloud-usage** data source and usage dashboard. Inspect active series, samples per second multiplied by 60, included DPM per series, cardinality growth, and rejected samples. Recheck after a deployment and representative peak; an empty test service does not establish production usage. Select the relevant stack in usage queries rather than summing unrelated stacks. Reduce ingestion at its source before exhausting the allowance. [Metrics pricing and usage metrics](https://grafana.com/docs/grafana-cloud/cost-management-and-billing/understand-your-invoice/metrics-invoice/)

## Honest windows and sparse traffic

Use `rate`/`increase` per writer before summing, and use summed failures divided by summed completions. `increase` extrapolates to window boundaries and may be fractional. It is useful for trends, not a billing or accounting ledger. One sample from a new short-lived counter cannot establish its increase; start timestamps and lifecycle-aware export need end-to-end validation.

Use `$__rate_interval` for exploratory trends and fixed windows for summary panels or alerts. The starter uses 15-minute summaries to help sparse apps, with volume beside the ratio. Zero denominators should remain undefined; absent counters should remain missing. Quantiles are approximate and unstable with very few observations. Retain gaps in graphs and investigate resets, duplicate writers, and stale samples.

Free-tier retention cannot substantiate a rolling 30-day SLO. Use a clearly labelled shorter window, existing provider history, or a separately designed longer-lived aggregate with adequate semantics. Multi-window burn alerts are an optional later step, not a prerequisite to monitoring a small application. [SLO alerting tradeoffs](https://sre.google/workbook/alerting-on-slos/)
