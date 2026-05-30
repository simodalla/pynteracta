# URL Construction

## API base URL

All API endpoints are rooted at:

```
{base_url}{base_path}/api/external/v{api_version}/{endpoint}
```

Example: `https://interacta.example.it/portal/api/external/v2/core/auth/current-user-data`

## Normalization rules

`build_api_base()` applies these rules in order:

1. Strip whitespace from `base_url` and `base_path`.
2. Ensure `base_url` has a scheme (defaults to `https://` if omitted).
3. Strip trailing `/` from `base_url`.
4. If `base_path` is empty, use `""`; otherwise ensure it starts with `/` and has no trailing `/`.
5. Join segments with a single `/`.

All four of these inputs produce the same canonical base `https://host/portal/api/external/v2`:

```python
build_api_base("https://host", "/portal", 2)
build_api_base("https://host/", "portal", 2)
build_api_base("host", "/portal/", 2)
build_api_base("https://host//", "//portal//", 2)
```

## Web URL helper

`InteractaClient.web_urls` generates deep-link URLs for use in dashboards or notifications.
Note the trailing slash on the user URL — this matches the Interacta web app routing.

```python
client.web_urls.post(21269)
# "https://interacta.example.it/portal/post/21269"

client.web_urls.user(5225)
# "https://interacta.example.it/portal/admin/user/5225/"

client.web_urls.community(79)
# "https://interacta.example.it/portal/community/79"
```

These URLs are also available via the CLI `--web-url` flag:

```bash
pynteracta posts get 21269 --web-url
pynteracta posts list --community 79 --all --web-url
pynteracta users get-for-edit 5225 --web-url
```
