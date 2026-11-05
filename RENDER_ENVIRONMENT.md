# BunChaViet: environment and Gmail OAuth

This document describes configuration only. It does not authorize deployment.
Never commit `.env`, OAuth JSON files, or actual secret values.

## Production detection

Production is enabled by `APP_ENV=production` **or** Render's automatic
`RENDER=true`. Setting `APP_ENV=local` cannot disable Render's production checks.
`DB_MODE=postgres` by itself is not a production flag, so developers can test
Neon locally. Production does not load a local `.env` file.

## Render variables

| Variable | Requirement | Example/placeholder |
| --- | --- | --- |
| `APP_ENV` | Recommended explicit production flag | `production` |
| `DB_MODE` | Required production value | `postgres` |
| `DATABASE_URL` | Required PostgreSQL URL with TLS | `postgresql://<USER>:<URL_ENCODED_PASSWORD>@<NEON_HOST>/<DATABASE>?sslmode=require&channel_binding=require` |
| `FLASK_SECRET_KEY` | Required, stable secret from environment | `<GENERATE_A_RANDOM_SECRET_OF_AT_LEAST_32_BYTES>` |
| `OTP_HMAC_SECRET` | Recommended separate stable secret; if omitted, Flask secret is used | `<GENERATE_ANOTHER_RANDOM_SECRET>` |
| `GMAIL_TOKEN_PATH` | Absolute path; default shown here | `/etc/secrets/gmail_token.json` |
| `GMAIL_ADDRESS` | Optional authorized sending address; otherwise Gmail API uses the authenticated account | `<AUTHORIZED_SENDER_EMAIL>` |
| `PORT` | Render supplies this; Gunicorn already reads it | `<RENDER_ASSIGNED_PORT>` |

`SECRET_KEY` is not an alias for `FLASK_SECRET_KEY`. Whitespace-only required
values are rejected. An explicitly blank `OTP_HMAC_SECRET` is rejected in
production. Use a pooled Neon URL as appropriate for the project; keep TLS
enabled. For stricter hostname verification, use `sslmode=verify-full` with the
required CA configuration. Never paste the URL into logs or screenshots.

Before serving requests, production verifies the Flask secret, PostgreSQL mode,
URL format/TLS, readable OAuth JSON with refresh credentials, and sender format
when supplied. Failures name the configuration item without displaying its value.
Startup does not connect to Neon or refresh/contact Google; successful startup
does not prove that the remote credentials are still valid.

## Flask sessions

Production cookies use `Secure`, `HttpOnly`, and `SameSite=Lax`.
Local HTTP cookies use `HttpOnly` and `SameSite=Lax`, without `Secure`.
The permanent session lifetime remains 30 days; OTP lifetime remains 5 minutes,
verified-email lifetime 15 minutes, and existing attempt/send limits are unchanged.
Secure cookies require HTTPS. A changed Flask key invalidates existing sessions;
a changed OTP HMAC key invalidates pending OTPs. Use stable values across restarts
and workers. SameSite is not a replacement for CSRF protection.

## Gmail OAuth secret file

1. Obtain the authorized-user OAuth token outside the deployed web process, using
   the existing local authorization workflow and `gmail.send` scope.
2. Supply the JSON as a Render secret file named `gmail_token.json`; do not add it
   to the repository, image, or build arguments.
3. Set `GMAIL_TOKEN_PATH` to the mounted absolute Linux path. The JSON must include
   the authorized-user refresh credentials (`refresh_token`, `client_id`,
   `client_secret`). These values are secrets; do not log them.
4. No SMTP/app password is used. The runtime sends via Gmail's HTTPS API.

The source token file is read-only from the application's perspective. Expired
or absent access tokens are refreshed in memory for the send operation; the app
never writes refreshed credentials to disk, including on Local. A read-only
mount therefore works. There is no new cache, external secret store, or paid
service. If the source file contains an expired access token, subsequent sends
may refresh again. Threads/processes can perform separate refreshes; do not
increase throughput without evaluating this behavior.

If Google revokes/expires the refresh authorization, obtain a replacement locally
and replace the secret through the platform. Rotated refresh tokens are not
persisted automatically. Google OAuth consent/test-mode policy and Gmail quotas
still apply. Startup checks structure, not delivery or account authorization.

## Local development

Local `.env` loading and SQL Server defaults remain available:

```dotenv
APP_ENV=local
DB_MODE=local
DB_SERVER=<LOCAL_SQL_SERVER>
DB_NAME=<LOCAL_DATABASE>
DB_USER=<LOCAL_DB_USER>
DB_PASSWORD=<LOCAL_DB_PASSWORD>
DB_DRIVER=<INSTALLED_ODBC_DRIVER>
FLASK_SECRET_KEY=<OPTIONAL_STABLE_LOCAL_SECRET>
GMAIL_TOKEN_PATH=<ABSOLUTE_LOCAL_OAUTH_JSON_PATH>
```

Without `FLASK_SECRET_KEY`, Local retains the `.flask_secret_key` fallback.
On Windows, the old `C:\BunChaVietSecrets\gmail_token.json` fallback is retained.
On non-production Linux, the default is `~/.config/bunchaviet/gmail_token.json`.
Windows drive/UNC paths are rejected on Linux. Production never creates or uses
the local secret-key file. `uv sync --locked` includes the Local ODBC package;
the production Docker image intentionally excludes it.

## Verification without real accounts

```text
python -B -m unittest test_runtime_environment
python -B -m unittest test_database_connection test_customer_auth test_admin_contacts test_admin_products test_admin_shippers test_admin_dashboard test_order_flows
```

These suites mock database writes and Google delivery. Do not run the legacy
live DB/Gmail scripts as part of this configuration check.

References: [Render environment variables](https://render.com/docs/environment-variables),
[Render secret files](https://render.com/docs/configure-environment-variables),
[Flask configuration](https://flask.palletsprojects.com/en/stable/config/).
