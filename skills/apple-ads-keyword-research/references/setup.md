# Apple Ads API access setup

## Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The script declares Python 3.11+ and `pyjwt[crypto]>=2.10,<3`; `uv run` resolves an isolated environment. It calls the Apple Ads Platform API v1 (`https://api.ads.apple.com/v1`) over HTTPS with the standard library.

Apple released the Platform API (version 1.0) in August 2026. It replaces the Campaign Management API v5, which Apple sunsets on January 26, 2027. This skill does not use v5. When maintaining it, check the [changelog](https://developer.apple.com/documentation/apple-ads-platform-api/changelog-apple-ads-platform-api) and update `API_BASE` and `API_VERSION` together.

You need an Apple Ads account with an App Store ad account: `doctor --ad-account-id ID` should list the `APPSTORE_APP_MANUAL` product feature. Apple Maps ad accounts (`BUSINESS_BRAND_MANUAL`) have no keyword insights and are out of scope.

## First-time access

1. Invite an API user. An account administrator signs in to [Apple Ads](https://ads.apple.com) (Advanced), opens Account Settings > User Management, and invites the user with an API role. This skill only reads, so ask for **API Account Read Only**, or **Limited Access: API Read Only** to restrict it to some resources. The invited user activates the account with the code Apple emails them. See [Implementing OAuth](https://developer.apple.com/documentation/apple-ads-platform-api/implementing-oauth-for-the-apple-ads-platform-api).
2. Generate a key pair locally, outside any repository:

   ```sh
   openssl ecparam -genkey -name prime256v1 -noout -out private-key.pem
   openssl ec -in private-key.pem -pubout -out public-key.pem
   chmod 600 private-key.pem
   ```

3. Upload the public key. Signed in as the API user, open Account Settings > API, paste the contents of `public-key.pem` (including the BEGIN and END lines), and save. Apple then shows a `clientId`, `teamId`, and `keyId`. Copy them into the configuration below.
4. Run `doctor`, then verify one ad account and run one small report or popularity query for a real market.

You do not need Apple's client-secret sample script. For each run, the CLI signs a client secret that expires after 10 minutes (Apple allows up to 180 days) and exchanges it for a one-hour access token. Neither is printed or written to disk. If the private key leaks, generate a new pair and replace the public key in Account Settings > API.

## Configuration

Choose one source. `--config` reads that TOML file and ignores the environment; without it the script reads environment variables.

Example external TOML, such as `~/.config/apple-ads/research.toml`:

```toml
client_id = "SEARCHADS.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
team_id = "SEARCHADS.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
key_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
# Absolute, ~-prefixed, or relative to this file.
private_key_path = "private-key.pem"
```

Unknown keys are rejected. Restrict the file and key to your user, for example with `chmod 600`. The key must be an unencrypted PEM P-256 private key; OpenSSL's `EC PRIVATE KEY` output and PKCS#8 both work.

Equivalent environment variables:

- `APPLE_ADS_CLIENT_ID`
- `APPLE_ADS_TEAM_ID`
- `APPLE_ADS_KEY_ID`
- `APPLE_ADS_PRIVATE_KEY_PATH`

Populate them from your secret manager or local environment. Keep credentials out of chat, repository files, exports, and shell arguments. The CLI refuses to write an export over the configuration file or the private key.

```sh
uv run scripts/apple_ads.py doctor --config ~/.config/apple-ads/research.toml
uv run scripts/apple_ads.py doctor --config ~/.config/apple-ads/research.toml --ad-account-id 123456789
```

The first command lists every ad account the credentials can reach, with your roles. Each token belongs to one organization. The second checks the ad-account-scoped call and reports the account's currency, time zone, status, and product features. Neither proves that reports or insights return data; run one of each for the intended market.

## Errors and verification

- **Configuration error:** the message names the missing or unknown field. Check the TOML syntax, the key path, and that the key is an unencrypted P-256 PEM.
- **OAuth `invalid_client`:** the client ID, team ID, or key ID is wrong, the uploaded public key does not match the private key, or the system clock is far off. Copy the three IDs again from Account Settings > API.
- **HTTP 401:** the token expired or was revoked. The CLI requests one fresh token per run before failing.
- **HTTP 403:** the API role cannot read that resource or ad account. Compare the roles `doctor` lists.
- **HTTP 404 or `ENTITY_NOT_FOUND`:** a wrong campaign, ad group, or Adam ID, or the wrong `--ad-account-id`.
- **HTTP 429:** the CLI paces requests with Apple's `RateLimit-*` headers and retries with `Retry-After`. Processes that share an ad account share its quota, so run this CLI serially per account. Retry later if the error persists.
- **Validation errors (HTTP 400):** the message includes Apple's error code, the field, and a short reason. Date span and granularity rules are listed in the [CLI reference](cli-and-metrics.md).

Offline tests need no credentials. With access, run `doctor`, `campaigns`, one keyword report, one search term report, and one `popularity` query for an explicit country. Check currency, time zone, returned periods, and exports. Report each live capability you could not run as unverified; mocked tests do not prove the live API behaves the same way.
