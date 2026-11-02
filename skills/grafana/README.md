# Grafana

Set up useful application monitoring for a solo maintainer with several web or mobile apps, mainly on GCP and AWS. The skill chooses a small ingestion setup, limits metric cardinality and frequency, and builds Grafana Cloud dashboards that show failures, latency, traffic, and missing telemetry.

It favors existing cloud metrics for serverless workloads, bounded custom metrics when they add useful evidence, and versioned dashboard JSON. It includes an app dashboard template, a local portfolio-dashboard generator, and an OTLP environment checklist. Alerting, Terraform, collectors, and client telemetry are added when the application needs them.

## Install

```sh
./coreskills install --tool codex --skills grafana
```

Replace `codex` with `claude`, `copilot`, or `gemini` for another tool.

## Use

Invoke the skill with `$grafana` in Codex or `/grafana` in Claude Code; automatic skill selection is disabled. Work from the application's repository so the assistant can inspect its runtime, deployment, and existing telemetry.

```text
Use $grafana to set up minimal Grafana Cloud monitoring for this Cloud Run API. Stay on the free tier and reuse existing metrics where possible.
```

```text
Use $grafana to add critical sync failures from this mobile app to our existing backend metrics, without putting Grafana credentials in the app.
```

```text
Use $grafana to create a portfolio dashboard for my applications and an app detail dashboard. Prepare the JSON locally first.
```

## Included resources

- [SKILL.md](SKILL.md): workflow, scope, and verification.
- [Ingestion](references/ingestion.md): OTLP, GCP, AWS, and mobile/browser paths.
- [Metrics and budget](references/metrics-and-budget.md): metric contract, free-tier estimates, and low-traffic semantics.
- [Dashboards](references/dashboards.md): rendering, importing, API/Terraform choices, and live checks.
- [App overview template](assets/app-overview.json) and [renderer](scripts/render_dashboards.py): local dashboard artifacts. Run `make grafana-test` from the repository root to test the renderer.
- [OTLP environment checklist](assets/otlp.env.example): server-side configuration inputs.
