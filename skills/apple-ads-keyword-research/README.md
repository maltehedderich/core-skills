# Apple Ads Keyword Research

A skill for reading Apple Ads campaign data and researching App Store keywords. Its Python CLI calls the Apple Ads Platform API for campaign, ad group, keyword, and search term reports, Apple's keyword and phrase suggestions, search term popularity by country and genre, and impression share. It only reads: the client sends GET requests and `/query` searches and refuses anything that could change a campaign.

Live data requires `uv`, Python 3.11 or newer, and an Apple Ads API user with a P-256 key pair uploaded in Apple Ads. A read-only API role is enough. `uv` installs the script's one dependency, PyJWT with its crypto extra, which signs Apple's client secret.

```text
Use $apple-ads-keyword-research to review last month's keyword and search term performance for my app in Germany. Flag search terms to add as exact keywords or negatives, and export the data.
```

For keyword discovery:

```text
Use $apple-ads-keyword-research to find relevant App Store keywords for my time-tracking app in Germany. Combine Apple's suggestions with search term popularity in the Productivity genre and explain the shortlist.
```

Apple reports popularity as relative scores and ranks without search counts, and the skill never converts them into volumes. Proposed keyword, negative, and bid changes come back as recommendations for you to apply.

- [Skill workflow](SKILL.md)
- [API access and credential setup](references/setup.md)
- [CLI examples and metric interpretation](references/cli-and-metrics.md)

From the skill directory:

```sh
uv run scripts/apple_ads.py --help
uv run scripts/apple_ads.py doctor --config ~/.config/apple-ads/research.toml
uv run scripts/apple_ads.py campaigns --ad-account-id 123456789 --adam-id 1234567890
uv run scripts/apple_ads.py report --ad-account-id 123456789 --level searchterms --campaign-id 444555666 --start 2026-09-01 --end 2026-09-30 --output searchterms.json --csv searchterms.csv
uv run scripts/apple_ads.py ideas --ad-account-id 123456789 --adam-id 1234567890 --country DE --output ideas-de.json
uv run scripts/apple_ads.py popularity --ad-account-id 123456789 --country DE --genre PRODUCTIVITY_UTILITIES --granularity monthly --start 2026-07-01 --end 2026-09-30 --output popularity-de.json
uv run --with 'pyjwt[crypto]>=2.10,<3' python -m unittest discover -s tests -v
```

The tests use a recorded fake transport and freshly generated keys, so they need no credentials or network access. They check request bodies, pagination, retries, error handling, and exports against Apple's documented schemas. Live verification requires configured credentials.
