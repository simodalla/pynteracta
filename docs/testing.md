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
PYNTERACTA_TEST_WRITE_POST_ID=790
PYNTERACTA_TEST_WRITE_COMMUNITY_ID=124
PYNTERACTA_TEST_WORKFLOW_POST_ID=791
```

`PYNTERACTA_TEST_WRITE_POST_ID` enables the **write** integration test (create → edit → delete of a
task). Point it at a post in a **test community**, never at production content: the test creates
a task on it and deletes it at the end. Leave it empty to skip the write test.

`PYNTERACTA_TEST_WRITE_COMMUNITY_ID` enables the **post write** integration test: it creates a post
in that community, edits it, adds a watcher and a comment, copies it, and deletes both posts at the
end (also when a step fails). It needs `PYNTERACTA_TEST_USER_ID` too (the watcher). Use a **test
community** only. If that community has required custom fields, put them in
`PYNTERACTA_TEST_WRITE_CUSTOM_DATA` as a JSON object; catalog and user references are written as
lists of ids (`{"2003": [89]}`), not as the objects the server returns when reading.
The same two variables enable the **attachment upload** integration test: it uploads a small
generated file, creates a post with it, uploads a second file as a new version of the attachment,
removes it, and deletes the post at the end (also when a step fails).
`PYNTERACTA_TEST_WORKFLOW_POST_ID` (optional) points at a post with a workflow:
the test only reads its workflow screen and never executes a transition.

The **group write** integration test (create → edit → add and remove a member → delete, also
when a step fails) runs with the variables above and `PYNTERACTA_TEST_USER_ID`, the user it adds
to the group. The **user write** integration test creates a **real user** on the tenant (a
licence, possibly notification emails), edits it, changes its credentials and deletes it: it
runs only with `PYNTERACTA_TEST_WRITE_USERS=1`; `PYNTERACTA_TEST_WRITE_USER_EMAIL_DOMAIN`
(default `example.com`) is the domain of the created user's email. Both tests print `[05-C26]`
lines with what the server did with omitted fields and with deletion.

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
