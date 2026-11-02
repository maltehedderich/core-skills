---
name: grafana
description: Set up lean application monitoring in Grafana Cloud for a solo maintainer running several web apps, APIs, mobile backends, or jobs on GCP or AWS. Use when adding metrics or monitoring to an app; sending OpenTelemetry (OTLP) or Prometheus metrics to Grafana Cloud; querying Cloud Run, Lambda, Cloud Monitoring, or CloudWatch metrics from Grafana; building or fixing app and portfolio dashboards; or keeping active series within the free tier. Also covers client-side health signals for mobile and browser apps and whether a first alert is worth adding.
---

# Grafana

Help one person answer: Are important user operations failing or slow? Which app or operation needs attention? Where should I investigate next?

Optimize for low maintenance across several applications. Start with existing telemetry, a small set of useful metrics, and a readable dashboard. Add infrastructure detail, collectors, client telemetry, or alerts when they answer a concrete operational question. Preserve the project's existing deployment and infrastructure tooling.

## Establish the smallest useful scope

Inspect the repository and deployment configuration before asking for details. Establish:

- Runtime and hosting model, especially Cloud Run CPU allocation, Lambda lifecycle, scaling, and background jobs.
- Existing instrumentation, metrics endpoints, cloud metrics, error tracking, and Grafana data sources.
- One to three critical operations, what counts as success or failure, and whether backend evidence covers the user experience.
- Expected production apps, environments, regions, peak concurrent metric writers, and current Grafana usage.

A monitoring setup request authorizes the necessary implementation within its stated scope. A request for a plan or review does not authorize changes to live apps or Grafana. Complete useful local work when credentials or account details are unavailable, then identify the exact missing input. Never claim delivery or a working dashboard from local validation alone.

## Choose ingestion before writing queries

Read [ingestion.md](references/ingestion.md) for the relevant hosting path. Distinguish **querying cloud metrics through a Grafana data source** from **storing pushed application metrics in Grafana Cloud Metrics**. Both can appear in Grafana Cloud; only the latter consumes its metrics ingestion allowance.

Prefer a small existing Alloy/OTel pipeline when available. A long-lived backend can send a bounded set of metrics through that pipeline, or directly over OTLP when running a collector is disproportionate; explain the reliability tradeoff. For request-based Cloud Run, Lambda, and short jobs, resolve export lifecycle limitations first. Do not change billing mode or add always-on infrastructure merely to make a timer run. Give every concurrent writer its own instance identity, generated at runtime; a fixed value in shared configuration merges independent counters into one corrupted series.

Keep Grafana write credentials on trusted servers. Mobile and browser clients use an existing crash/RUM service or a bounded, authenticated backend event endpoint. Read the client section of the ingestion reference when user experience extends beyond the API.

Check current official documentation for the selected SDK, exporter, cloud authentication, and Grafana API before implementing their configuration. Use Context7 when available, otherwise official vendor documentation. The references record the design decisions and sources; they are not frozen API specifications.

## Limit metrics deliberately

Read [metrics-and-budget.md](references/metrics-and-budget.md) before adding instruments or collection jobs. Reuse an existing suitable metric contract; the bundled dashboard contract is a fallback, not a reason to duplicate all HTTP instrumentation.

Default to production only, roughly 60-second export/scrape intervals, bounded operation names, and the minimum useful histogram dimensions. Set histogram boundaries explicitly; OTel SDK defaults are scaled for milliseconds. Estimate both series and samples across the whole portfolio, including concurrent writers, instance churn, and existing integrations. Keep meaningful headroom below the account's current allowance. Verify actual usage after rollout.

Do not enable broad host/Kubernetes integrations, all automatic SDK metrics, all logs, traces, profiles, service graphs, or prebuilt alert packs by default. Keep existing cloud logs available through links. Add a signal when it helps resolve a known question.

## Build a dashboard that tells the truth

Read [dashboards.md](references/dashboards.md). Use versioned dashboard JSON and Grafana's import UI for an initial setup. Reuse Terraform when the project already manages Grafana with it; use the supported HTTP API for repeated automation. No new CLI or Terraform state is required just to create a dashboard.

The bundled [app overview](assets/app-overview.json) and [renderer](scripts/render_dashboards.py) produce an app detail view and a portfolio view with a persistent row for every configured app. Map their metric contract to verified series, or adapt the queries to native cloud data sources. Do not import empty PromQL panels and call a cloud-data-source setup complete.

Keep user-operation volume, failures, latency, and telemetry freshness together. Use precise titles, units, and windows. Distinguish an observed zero, no traffic, and absent telemetry. Keep known apps selectable when they stop reporting. A recent sample from one instance does not establish that the entire fleet is reporting.

Use `rate` or `increase` on each counter before aggregation. Divide summed failures by summed eligible operations. Aggregate compatible histograms before computing quantiles. Never average per-instance percentages or p95s. Keep error volume visible beside percentages for low-traffic apps.

Link to provider logs, existing error tracking, and relevant deployment history. Preserve app, environment, and incident time where the destination supports it. Add capacity panels only for plausible bottlenecks. Do not invent SLO targets or show a 30-day calculation from 14 days of retained data.

## Alerts are a separate small decision

Dashboard delivery does not require an alerting project. If unattended detection is wanted, prefer an existing uptime check or one external check per important public app. Start with one actionable notification path, sustained failure, a useful link, and explicit no-data behavior. Add missed-job checks only for jobs with deadlines. Avoid percentage-only alerts on sparse traffic and infrastructure alerts without a response. Introduce burn-rate alerting only with a defined SLO, sufficient traffic, and adequate retained history.

## Verify and hand over

With the available access, test a successful operation, a failure, no traffic, and missing telemetry. For custom export, also test restart, two concurrent writers, and the hosting lifecycle (idle/scale-to-zero or invocation completion). Confirm the actual metric names, labels, units, temporality, and bucket representation in Grafana before finalizing queries. Check that ingestion failure never breaks a user request.

Import and inspect the rendered dashboard when a Grafana instance is available. Check variable selection, portfolio links, null states, and incident time ranges. Compare counts with application evidence, allowing for `increase` extrapolation and collection gaps. Inspect usage and rejected samples after a representative workload and deployment cycle.

Report the chosen path, changed files, dashboard location or import files, estimated and observed usage, checks performed, and any remaining credentials or rollout steps. Clearly distinguish prepared, deployed, and verified work.
