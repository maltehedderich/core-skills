# Ingestion choices

Sources checked 2026-11-02. Recheck SDK support, account settings, and cloud authentication when applying this skill.

## Choose the shortest reliable path

| Situation | Starting point | What to establish |
| --- | --- | --- |
| Existing Prometheus or OTel pipeline | Allowlist useful application metrics and reuse its Grafana destination | Avoid duplicate collection and unintended labels |
| Long-lived VM/container backend | Existing Alloy/OTel collector; otherwise consider direct SDK OTLP | Bounded queues, retry behavior, shutdown flush, export failures |
| Cloud Run with request-based CPU | Query built-in Cloud Monitoring metrics from Grafana first | Platform metrics cover requests, not all business outcomes; background timers can stall |
| Cloud Run with instance-based CPU | SDK OTLP, optionally through an existing sidecar | CPU available, startup/shutdown order, cost and writer identity |
| Lambda or short-lived jobs | Native CloudWatch/provider metrics first; lifecycle-aware exporter only when needed | Freeze, first sample, timeouts, final flush, invocation overhead |
| Mobile/browser application | Backend metrics plus existing crash/error tooling | API success does not prove client or offline operation success |

Grafana recommends a collector for production. Direct SDK export is a deliberate simplicity tradeoff for a small trusted backend: fewer components, but weaker buffering and centralized filtering. Explain that tradeoff instead of calling it Grafana's production recommendation. Do not build a shared collector service solely for a handful of metrics unless lifecycle or delivery needs justify operating it. [Grafana OTLP ingestion](https://grafana.com/docs/grafana-cloud/send-data/otlp/send-data-otlp/)

## Push application metrics over OTLP

1. Find the stack's **OpenTelemetry** connection details. Use its exact endpoint and instance ID; do not derive the region or reuse a different product's numeric ID.
2. Reuse the stack's hosted Prometheus data source for queries. Creating another data source does not enable ingestion.
3. Use a stack-scoped Cloud Access Policy token with `metrics:write`. Keep it in the existing secret store. This token is distinct from the Grafana service-account token used to manage dashboards.
4. Configure a metrics provider, reader, exporter, and explicit instruments/views for the application's SDK. Environment variables alone do not instrument an application, and support varies by SDK.
5. Start with cumulative counters/histograms, approximately 60-second collection, bounded export timeouts/queues, and bounded retries. Check end-to-end support before selecting delta temporality. Some Prometheus conversion paths require stateful delta-to-cumulative conversion.
6. Export only the selected metric families. Disable automatic trace/log export unless requested.
7. Give every concurrent writer a unique `service.instance.id`, generated at process start (a random UUID, or the platform's instance, task, or pod ID) unless the SDK already sets one. Do not put a fixed value in shared deployment configuration: every replica would inherit it, and their independent cumulative counters would interleave in one series and corrupt `rate`/`increase`. Do not collapse instance identity to save series; budget for the churn instead.

Use [otlp.env.example](../assets/otlp.env.example) as a configuration checklist. Supply the secret at runtime; Base64 authentication is still a credential. A generic OTLP base endpoint receives `/v1/metrics` from an HTTP exporter; a signal-specific metrics endpoint must include the full path. Verify this in the selected SDK. The SDK should continue serving requests if telemetry is unavailable, and report exporter failures through existing local logs without exposing secrets.

OTLP resource attributes are not automatically identical to metric labels. Grafana maps `service.name` (with optional namespace) to `job`, and `service.instance.id` to `instance`. Other resource attributes can live in `target_info` or be promoted according to stack settings. The bundled contract uses explicit metric attributes `app`, `environment`, and `operation` so its filters do not depend on implicit promotion. Inspect ingested labels and prevent unintended version, pod, or user dimensions from multiplying every metric. [Format considerations](https://grafana.com/docs/grafana-cloud/send-data/otlp/otlp-format-considerations/), [attribute promotion](https://grafana.com/docs/grafana-cloud/send-data/otlp/promote-resource-attributes/)

For a Prometheus endpoint, use an existing Alloy/Prometheus scrape and remote-write path. Scrape actual instances through service discovery; scraping a load balancer can interleave independent counters. Ordinary Prometheus exposition text is not a remote-write or OTLP payload. Do not POST it directly to Grafana's remote-write URL. Keep scrape endpoints private and filter at the sender. Pushgateway is not a general-purpose replacement for application metric export.

## GCP

For Cloud Run's default request-based billing, CPU can be unavailable between requests, including in sidecars. A 60-second exporter timer can miss sparse traffic or process shutdown. A sidecar alone does not solve this. Use existing platform metrics through the **Google Cloud Monitoring data source** for the initial request/error/latency view. Add custom business metrics only where platform metrics lack the needed evidence. [Cloud Run CPU and billing](https://docs.cloud.google.com/run/docs/configuring/billing-settings), [Cloud Run monitoring](https://docs.cloud.google.com/run/docs/monitoring)

If custom push is essential, compare a supported serverless collector/extension, bounded export during the active request lifecycle, and instance-based CPU. A request-scoped flush adds latency/cost and still cannot guarantee accounting accuracy; benchmark it and keep telemetry failures non-fatal. Do not silently enable minimum instances or change billing. For short-lived cumulative counters, validate the first observations: a single exported sample is insufficient for a rate and can lose the initial increment unless the pipeline supports start timestamps appropriately.

Configure Grafana Cloud's Google Cloud Monitoring data source with supported authentication, preferably federation when available, and narrowly scoped read access. Verify the project, monitored resource, service, region, status-class fields, metric type, and alignment semantics in Explore. Do not apply Prometheus `rate` mechanically to provider DELTA metrics. Provider-managed metrics can cover failures that never reach the app. [GCP data source](https://grafana.com/docs/grafana/latest/datasources/google-cloud-monitoring/), [authentication options](https://grafana.com/docs/learning-hub/intro-to-cp-olly/03-data-sources/24-gcp-cloud-monitoring-data-source/)

Direct queries leave data in GCP; they do not consume hosted Prometheus storage. Custom metrics, log-based metrics, provider API usage, egress, and additional compute can have separate charges. Do not enable a cloud-wide ingestion integration by default.

## AWS

Use **CloudWatch as a Grafana data source** for existing Lambda, API Gateway, ALB, and queue metrics. Choose only resources and statistics that answer the app's questions. For Lambda start with invocations, errors, throttles, and duration; verify API-layer errors separately. A successful Lambda invocation may still return an unsuccessful business or HTTP response. Query counts with the appropriate `Sum` and periods; do not average percentages or independently calculated percentiles across resources.

Use supported role-based authentication with least-privilege read access and verified account/region. Grafana Cloud's cross-account mechanism differs from a local AWS profile. CloudWatch `GetMetricData` queries can cost money even when Grafana is free: use modest refresh intervals, narrow dimensions, and avoid permanently displayed 5-second-refresh dashboards. CloudWatch data sources query in place; CloudWatch scrape/stream integrations copy data and add ingestion usage. [CloudWatch data source and pricing](https://grafana.com/docs/grafana/latest/datasources/aws-cloudwatch/), [data source versus ingestion](https://grafana.com/docs/learning-hub/intro-to-cp-olly/00-intro/02-two-approaches/)

For custom Lambda metrics, reuse an existing supported extension or provider-side metric emission path. Ordinary Lambda environments freeze after invocation, so periodic SDK export and shutdown-only flushes are insufficient. Validate cold and warm invocations and the first counter sample. Check the actual Lambda execution model; continuously running variants differ. ECS/EC2 can use the long-lived backend path. [Lambda lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)

## Mobile and browser signals

Never embed a Grafana ingestion token in an app bundle or browser script. Do not expose an unrestricted public OTLP proxy with a private token behind it.

Keep existing crash reporting or RUM if it provides the answer. Link its filtered issue view from Grafana. A link is useful context but is not a Grafana-hosted client-health metric; state this limit. If the user needs client outcomes in Grafana, send only a few allowlisted events to an existing authenticated backend endpoint, with bounded payloads, validation, rate limits, and a defined retry/deduplication policy. Aggregate on the server into low-cardinality metrics. For unauthenticated apps, use an established public-client telemetry collector with abuse controls instead of inventing credential secrecy.

Track a critical outcome such as sync completion or purchase confirmation, and client crashes only with a valid denominator and collection coverage. Client reports can arrive late or never arrive; server-observed client events are not a complete census of client failures. Do not label metrics by user, device, session, raw URL, exception text, or unbounded app version. If release/platform splits are needed, bound them and count their cost. Avoid building a new analytics ingestion service just to fill a panel.
