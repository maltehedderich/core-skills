# Google Ads access setup

## Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The script declares Python 3.11+ and `google-ads>=32,<33`; `uv run` resolves an isolated environment. API v25 is explicit so an SDK update cannot silently change the wire API. When upgrading, check the [API sunset schedule](https://developers.google.com/google-ads/api/docs/sunset-dates), update the declared version and dependency together, and rerun the offline tests and live smoke checks.

You need a production Google Ads customer accessible to the consenting Google user. The script does not create accounts or campaigns. A manager customer ID used for login is different from the target customer ID used to retrieve data.

## First-time access

1. Create or select a Google Cloud project and enable the Google Ads API. Use the [current onboarding guide](https://developers.google.com/google-ads/api/docs/get-started/introduction).
2. Apply for **Basic** access in that project's Google Ads API overview. Complete any required brand verification. Explorer excludes `KeywordPlanIdeaService`; Test access is insufficient for production research. Standard access also works when its permissible use includes keyword research. Follow [Google's access requirements](https://developers.google.com/google-ads/api/docs/api-policy/access-levels) and accurately describe the intended use; Google controls approval.
3. Configure the OAuth consent screen and a **Desktop app** OAuth client in the same project. Follow Google's [user authentication workflow](https://developers.google.com/google-ads/api/docs/oauth/user-authentication) and [Python authentication examples](https://developers.google.com/google-ads/api/docs/client-libs/python/authentication) to obtain a refresh token with the `https://www.googleapis.com/auth/adwords` scope. Perform interactive consent locally with the Google user that can access the customer. Follow current Google instructions for consent-screen publishing/testing status and token expiry.
4. Store the client ID, client secret, and refresh token in a local external configuration file or secret-managed environment. Keep credentials out of chat, repository files, exported results, and shell command arguments.
5. Run `doctor`, then run a planning check with your actual market and one relevant keyword.

**Developer token change:** Google sunset developer tokens on September 9, 2026. Access is now attached to the Cloud project owning OAuth credentials. Do not apply through the old manager-account API Center. The script supports token-free configuration; legacy developer-token settings remain accepted by the client. See [the migration guide](https://developers.google.com/google-ads/api/docs/api-policy/developer-token) and [client v32 changelog](https://github.com/googleads/google-ads-python/blob/main/ChangeLog). Recheck those sources when maintaining this setup guide.

## Configuration

Choose one source. `--config` selects that YAML file; without it the script uses environment variables. It deliberately rejects `GOOGLE_ADS_CONFIGURATION_FILE_PATH` to avoid an implicit configuration-file override.

Example external YAML, such as `~/.config/google-ads/research.yaml`:

```yaml
client_id: "YOUR_OAUTH_CLIENT_ID"
client_secret: "YOUR_OAUTH_CLIENT_SECRET"
refresh_token: "YOUR_REFRESH_TOKEN"
use_proto_plus: true
# Only when accessing the customer through a manager:
# login_customer_id: "1234567890"
```

Restrict this file to your user, for example with `chmod 600`. Customer IDs in configuration must omit hyphens. The CLI accepts hyphens in `--customer-id`. It ignores configuration logging settings to avoid request/response logs.

Equivalent environment variable names:

- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`
- `GOOGLE_ADS_USE_PROTO_PLUS=true`
- Optional `GOOGLE_ADS_LOGIN_CUSTOMER_ID`

Use your secret manager or local environment setup to populate values. The script never writes or prints credentials. Other authentication modes supported by the official SDK can be supplied through its configuration, but the documented first-time flow uses user OAuth.

```sh
uv run scripts/google_keywords.py doctor --config ~/.config/google-ads/research.yaml --customer-id 1234567890
uv run scripts/google_keywords.py doctor --config ~/.config/google-ads/research.yaml --customer-id 1234567890 --check-planning --keyword 'time tracking' --geo-id 2840 --language-id 1000
```

The second example is explicitly US/English. Replace those IDs for your intended market. The first command verifies customer access and reports currency and whether it is a test account. It **does not prove planning access**. The second performs a real, quota-consuming historical-metrics call; an empty result can still establish that planning access works.

## Errors and verification

- **Configuration error:** check the named source, OAuth fields, and `use_proto_plus=true`. Do not send secrets when sharing diagnostics.
- **OAuth or permission error:** check the consenting user, token expiry/revocation, target customer, optional manager login, and project containing the OAuth client.
- **Planning denied:** confirm Basic/Standard access and permitted use in Google Cloud. The SDK cannot grant access. Retain the safe error code and request ID for support.
- **Quota/transient error:** the script paces planning RPCs and makes at most three attempts. Multiple processes sharing a customer also share the limit; run this CLI serially for that customer. Retry later for exhausted daily quota.
- **Test account:** use an accessible production customer for meaningful keyword research.

Offline tests require no credentials. Once access is available, run one `ideas` request and one `metrics` request for the same explicit market; check currency, months, and exports. For forecast verification, also run one `forecast` request using a real affordable budget, CPC cap, and explicit future dates; check account timezone, period totals, null fields, and exports. These are read-only planning calls. Report each unverified live capability as pending rather than interpreting mocked tests as API validation.

The separate `scripts/search_viability.py` calculator requires no Google access or SDK. It can establish economics before authentication, and evaluate saved exports after research. Missing live access is an INCOMPLETE viability assessment, not zero demand or a reason to invent forecast data.
