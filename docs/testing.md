# Testing

## Unit tests

Unit tests use `respx` to mock HTTP calls and require no network access. A bare `pytest` run
collects unit **and** contract tests (integration tests skip themselves unless opted in).

```bash
uv run pytest                                    # all unit tests
uv run pytest tests/unit/test_transport.py       # single file
uv run pytest --cov --cov-fail-under=85          # with coverage gate
```

## Contract tests

Contract tests validate that the **generated** Pydantic models still cover every property of the
pinned `tests/fixtures/swagger.json` schema, and smoke-parse the hand-written facades from the JSON
payload fixtures.

```bash
uv run pytest -m contract
```

To regenerate the auto-generated models from a new schema:

```bash
uv run python scripts/generate_models.py
uv run pytest -m contract
```

## Integration tests

Integration tests hit a **real Interacta tenant** and are opt-in.
They are skipped automatically if the required environment variables are missing.

### Prerequisites

You need:

- The **base URL** of your Interacta tenant (e.g. `https://my-tenant.interacta.io`).
- A **service account key** JSON file, downloadable from the Interacta admin console.
- Optionally: the integer IDs of a community, a user, and a post to use as test fixtures.

### Step 1 — place the service account key

```bash
mkdir -p tests/integration/.secrets
cp /path/to/your-key.json tests/integration/.secrets/sa.json
chmod 600 tests/integration/.secrets/sa.json
```

The `.secrets/` directory is git-ignored and will never be committed.

### Step 2 — create the `.env` file

```bash
cp tests/integration/.env.example tests/integration/.env
```

Edit `tests/integration/.env` with your real values:

```dotenv
PYNTERACTA_BASE_URL=https://my-tenant.interacta.io
PYNTERACTA_BASE_PATH=/portal
PYNTERACTA_API_VERSION=2
PYNTERACTA_SERVICE_ACCOUNT_KEY=tests/integration/.secrets/sa.json
PYNTERACTA_TEST_COMMUNITY_ID=123
PYNTERACTA_TEST_USER_ID=456
PYNTERACTA_TEST_POST_ID=789
```

### Step 3 — export the variables into your shell

pytest does not load `.env` files automatically:

```bash
export $(grep -v '^#' tests/integration/.env | xargs)
```

### Step 4 — run the tests

```bash
uv run pytest -m integration -v
```

To run only the authentication test:

```bash
uv run pytest tests/integration/test_auth_integration.py -v
```

### Skip behaviour

If a required environment variable is unset, or `sa.json` does not exist,
the individual test is **skipped** (not failed). This means you can run the
full test suite without any integration setup and nothing will break.
