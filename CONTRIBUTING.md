# Contributing to pynteracta

## Development environment

```bash
git clone https://gitlab.com/pynteracta/pynteracta.git
cd pynteracta
uv sync
uv run pre-commit install
```

## Branch and commit conventions

- Branch names: `feature_<short_name>` or `m<N>_<short_name>` for milestone work.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `test:`, `build:`, `ci:`, `chore:`.
- `BREAKING CHANGE:` footer triggers a major version bump (post v1.0).
- Pre-commit hooks enforce the commit format automatically.

## Pull request checklist

- [ ] `uv run ruff check . && uv run ruff format --check .` passes.
- [ ] `uv run mypy src` passes (strict).
- [ ] `uv run pytest -m "not integration and not contract" --cov --cov-fail-under=85` passes.
- [ ] `uv run pytest -m contract` passes.
- [ ] New public functions/classes have Google-style docstrings.
- [ ] All Python source files carry `# SPDX-License-Identifier: Apache-2.0` at the top.

## Running the test tiers

```bash
uv run pytest                            # unit tests (default)
uv run pytest -m contract               # contract tests (require tests/fixtures/swagger.json)
uv run pytest -m integration            # integration tests (opt-in, hits real tenant)
uv run pytest --cov --cov-fail-under=85 # with coverage gate
```

Integration tests require a service-account key and env vars — see
`tests/integration/.env.example` for the full list.

## How to add a new endpoint

1. **Regenerate models** — bump the Swagger snapshot if needed, then run
   `uv run python scripts/generate_models.py`. Commit the updated
   `src/pynteracta/models/generated/external_v2.py`.

2. **Write or extend the facade model** — add a class in the appropriate
   `src/pynteracta/models/facade/` file. Use `ConfigDict(extra="ignore")` and
   expose `.raw` as the escape hatch for generated-DTO fields the facade does
   not yet surface.

3. **Add the resource method** — add an explicit-kwargs method to the relevant
   `src/pynteracta/api/` client. Also add a `*_raw(req: DTO)` escape hatch for
   callers with pre-built DTOs.

4. **Add unit + contract tests** — at least one respx-mocked unit test per new
   method; a contract test validating the facade against a pinned JSON fixture.

5. **Expose in the CLI** — add a subcommand in `src/pynteracta/cli/` if the
   endpoint makes sense for interactive use. Add snapshot tests via
   `typer.testing.CliRunner` + `syrupy`.

6. **Update docs** — add or update `docs/api/` and `docs/cli.md`. Run
   `uv run mkdocs build --strict` to confirm the site builds.

## License

Contributions are accepted under the [Apache-2.0 license](LICENSE).
