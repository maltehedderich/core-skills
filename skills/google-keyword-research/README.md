# Google Keyword Research

A skill for researching Google keywords for SEO and paid search. Its Python CLI retrieves ideas, historical metrics, and read-only campaign forecasts through the Google Ads API. For paid-search viability, an offline calculator prices commercial clusters against contribution-based CAC, CPA, and CPC ceilings before recommending a test.

Live data requires `uv`, Python 3.11 or newer, a production Google Ads customer, and a Google Cloud project with keyword planning access. `uv` installs the API script's dependencies. The offline calculator uses Python's standard library and saved exports. No campaign or account changes are made.

```text
Use $google-keyword-research to research keywords for my time-tracking app in Germany, in German. Compare SEO and paid-search opportunities and export the data.
```

For a first paid test:

```text
Use $google-keyword-research to run the Search Viability Loop for my offer. Establish contribution-based CPC ceilings before building keyword clusters, forecast the surviving terms, and deliver a go/no-go decision with CSV and JSON exports.
```

Simple SEO and raw-metrics requests remain lightweight. The viability workflow produces a decision sheet, keyword and negative exports, and a proposed test brief. Missing evidence yields INCOMPLETE; an economics-only READY result is not a launch decision. Numeric defaults are adjustable assumptions, and forecasts disclose v25's missing negative/network controls.

- [Skill workflow](SKILL.md)
- [Authentication and access setup](references/setup.md)
- [CLI examples and metric interpretation](references/cli-and-metrics.md)
- [Search Viability Loop](references/search-viability-loop.md)
- [Offline calculator and input format](references/viability-calculator.md)

From the skill directory:

```sh
uv run scripts/google_keywords.py --help
uv run scripts/google_keywords.py ideas --customer-id 1234567890 --keyword Zeiterfassung --geo-id 2276 --language-id 1001 --output ideas.json
uv run scripts/google_keywords.py ideas --customer-id 1234567890 --site example.com --geo-id 2276 --language-id 1001 --output site-ideas.json
uv run scripts/google_keywords.py metrics --customer-id 1234567890 --keywords-file keywords.txt --geo-id 2276 --language-id 1001 --from-month 2025-01 --to-month 2025-12 --output metrics.json
uv run scripts/search_viability.py --help
uv run scripts/search_viability.py scaffold --historical metrics.json --profile-id buyers --input plan.json --output buyers-keywords.json
uv run scripts/search_viability.py evaluate --input plan.json --output decision.json --forecast-plans plans/
uv run --with 'google-ads>=32,<33' python -m unittest discover -s tests -v
```

API tests use actual SDK message types with mocked service responses; calculator tests use local fixtures. Run calculator-only tests without API dependencies with `uv run --python ">=3.11" python -m unittest discover -s tests -p test_search_viability.py -v`. Live verification requires configured credentials and planning access.
