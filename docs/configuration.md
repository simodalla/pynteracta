# Configuration

## Precedence (highest wins)

1. **CLI flags** — e.g. `--base-url`, `--profile`.
2. **Environment variables** — `PYNTERACTA_*` prefixed.
3. **Config file profile** — selected by `--profile` / `PYNTERACTA_PROFILE` / `current_profile`.
4. **Built-in defaults** — e.g. `base_path = "/portal"`, `timeout_seconds = 30.0`.

## Config file

Location: `platformdirs.user_config_dir("pynteracta") / "config.toml"`.

- Linux/macOS: `~/.config/pynteracta/config.toml`.
- Override with `PYNTERACTA_CONFIG_FILE` or `--config-file`.

```toml
current_profile = "default"

[profiles.default]
base_url        = "https://interacta.example.it"
base_path       = "/portal"
api_version     = 2
service_account_key = "~/.config/pynteracta/sa.json"
token_cache     = "file"
timeout_seconds = 30.0
log_level       = "INFO"

[profiles.staging]
base_url        = "https://staging.interacta.example.it"
service_account_key = "~/.config/pynteracta/sa-staging.json"
```

## Managing profiles

```bash
pynteracta config add-profile staging --base-url https://staging.interacta.example.it
pynteracta config use-profile staging
pynteracta config set service_account_key ~/.config/pynteracta/sa-staging.json
pynteracta config list
```

## Environment variables

| Variable | Profile field |
|---|---|
| `PYNTERACTA_PROFILE` | active profile name |
| `PYNTERACTA_BASE_URL` | `base_url` |
| `PYNTERACTA_BASE_PATH` | `base_path` |
| `PYNTERACTA_API_VERSION` | `api_version` |
| `PYNTERACTA_AUTH_METHOD` | `auth_method` (`service_account` or `google_oauth2`) |
| `PYNTERACTA_SERVICE_ACCOUNT_KEY` | `service_account_key` |
| `PYNTERACTA_GOOGLE_OAUTH2_TOKEN` | `google_oauth2_token` (not persisted to config) |
| `PYNTERACTA_TOKEN_CACHE` | `token_cache` (`file` or `memory`) |
| `PYNTERACTA_TOKEN_CACHE_DIR` | `token_cache_dir` |
| `PYNTERACTA_TIMEOUT` | `timeout_seconds` |
| `PYNTERACTA_LOG_LEVEL` | `log_level` |
| `PYNTERACTA_CONFIG_FILE` | config file path override |

## Profile fields

| Field | Type | Default | Description |
|---|---|---|---|
| `base_url` | `HttpUrl` | — (required) | Interacta tenant URL |
| `base_path` | `str` | `/portal` | URL path prefix |
| `api_version` | `int` | `2` | API version |
| `auth_method` | `"service_account"` or `"google_oauth2"` | `service_account` | Authentication method |
| `service_account_key` | `Path` | `None` | Path to SA key JSON |
| `google_oauth2_token` | `str` | `None` | Google access token; supply via env/flag, **not** persisted to config |
| `token_cache` | `"file"` or `"memory"` | `file` | Cache backend |
| `token_cache_dir` | `Path` | platformdirs user cache | Override cache directory |
| `timeout_seconds` | `float` | `30.0` | HTTP timeout |
| `log_level` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | `INFO` | Log verbosity |
