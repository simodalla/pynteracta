# SPDX-License-Identifier: Apache-2.0
"""Generate Pydantic v2 models from the Interacta external_v2 Swagger snapshot.

Usage::

    uv run python scripts/generate_models.py           # download + generate
    uv run python scripts/generate_models.py --offline  # regenerate from committed snapshot

The Swagger is sourced from the cert tenant (Q12 decision: v0.1 uses cert as canonical source;
production tracking deferred). See PROGRESS.md § M3 for context.

The API spec is Swagger 2.0, which datamodel-code-generator only supports when definitions are
lifted into components/schemas (OpenAPI 3.0 envelope). This script performs that conversion in a
temporary file before invoking codegen; the committed snapshot stays as-is (Swagger 2.0).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SWAGGER_URL = (
    "https://cert.development.lab.interacta.space/portal/api/swagger.json?filterByType=external_v2"
)
SWAGGER_SNAPSHOT = REPO_ROOT / "tests" / "fixtures" / "swagger.json"
GENERATED_OUT = REPO_ROOT / "src" / "pynteracta" / "models" / "generated" / "external_v2.py"


def stable_definitions_order(new: dict, previous: dict | None) -> dict:  # type: ignore[type-arg]
    """Riordina le ``definitions`` di ``new`` secondo l'ordine di ``previous`` (spec 09).

    datamodel-code-generator assegna i suffissi (``1``, ``Model``) alle definizioni omonime
    nell'ordine in cui le incontra: se il tenant riordina lo swagger, le classi generate cambiano
    nome. Qui le definizioni già note restano nell'ordine del pinnato precedente e le nuove vanno
    in coda, nell'ordine ricevuto; quelle sparite sono tolte. Il resto dello swagger non cambia.
    """
    definitions = new.get("definitions", {})
    if previous is None:
        return new
    known = [name for name in previous.get("definitions", {}) if name in definitions]
    known_set = set(known)
    added = [name for name in definitions if name not in known_set]
    return {**new, "definitions": {name: definitions[name] for name in known + added}}


def _read_previous_snapshot() -> dict | None:  # type: ignore[type-arg]
    """Il pinnato attuale, o ``None`` se manca o non è leggibile (con un avviso)."""
    if not SWAGGER_SNAPSHOT.exists():
        return None
    try:
        previous = json.loads(SWAGGER_SNAPSHOT.read_bytes())
    except ValueError as exc:
        print(
            f"WARNING: pinned swagger unreadable ({exc}); keeping the received order",
            file=sys.stderr,
        )
        return None
    return previous if isinstance(previous, dict) else None


def download_swagger() -> None:
    """Scarica lo swagger e lo scrive in ``tests/fixtures/swagger.json``.

    Le definizioni mantengono l'ordine del pinnato precedente (:func:`stable_definitions_order`);
    il file è JSON compatto, senza escape dei caratteri non ASCII, con a capo finale. Se la
    risposta non è uno swagger (JSON non valido, niente ``definitions`` o vuote) lo script esce
    con errore e il pinnato resta com'è; un pinnato precedente illeggibile dà solo un avviso.
    """
    print(f"Downloading Swagger from {SWAGGER_URL} …", flush=True)
    try:
        response = httpx.get(SWAGGER_URL, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"ERROR: Swagger download failed: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        received = response.json()
    except ValueError as exc:
        print(f"ERROR: the response is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    definitions = received.get("definitions") if isinstance(received, dict) else None
    if not isinstance(definitions, dict) or not definitions:
        print("ERROR: the response has no swagger definitions; pinned file kept", file=sys.stderr)
        sys.exit(1)

    previous = _read_previous_snapshot()
    ordered = stable_definitions_order(received, previous)
    # JSON compatto con a capo finale, come lo lascia il hook end-of-file-fixer di pre-commit.
    content = json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    SWAGGER_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SWAGGER_SNAPSHOT.write_bytes(content)
    print(f"Saved {len(content):,} bytes → {SWAGGER_SNAPSHOT}", flush=True)


def _to_oas3(swagger2: dict) -> dict:  # type: ignore[type-arg]
    """Lift Swagger 2.0 ``definitions`` into an OpenAPI 3.0 ``components/schemas`` envelope.

    The committed snapshot stays in its original Swagger 2.0 format; this conversion is
    performed in-memory only so that datamodel-code-generator can process it.
    """
    return {
        "openapi": "3.0.0",
        "info": swagger2.get("info", {"title": "pynteracta", "version": "0.1"}),
        "paths": {},
        "components": {"schemas": swagger2.get("definitions", {})},
    }


_PATCHED_FIELDS = {
    "customData",
    "currentWorkflowScreenData",
    "workflowScreenData",
    "screenData",
    "newScreenData",
}


def _patch_schema(oas3: dict) -> dict:  # type: ignore[type-arg]
    """Patch fields whose additionalProperties is typed as a plain object.

    The Swagger schema declares customData, currentWorkflowScreenData, workflowScreenData,
    screenData and newScreenData with
    ``additionalProperties: {"type": "object"}``, which the code generator maps to
    ``dict[str, dict[str, Any]]``. The real API returns heterogeneous values (null,
    lists, strings) for these keys, so the inner type must be ``Any``.

    Replacing with ``additionalProperties: {}`` (= any JSON value) causes the
    generator to emit ``dict[str, Any]`` instead.
    """
    schemas = oas3.get("components", {}).get("schemas", {})
    for schema in schemas.values():
        props = schema.get("properties", {})
        for field_name in _PATCHED_FIELDS:
            if field_name in props:
                field = props[field_name]
                if field.get("additionalProperties") == {"type": "object"}:
                    field["additionalProperties"] = {}
    return oas3


def run_codegen() -> None:
    """Run ``datamodel-code-generator`` on the committed Swagger snapshot."""
    if not SWAGGER_SNAPSHOT.exists():
        print(
            f"ERROR: Swagger snapshot not found at {SWAGGER_SNAPSHOT}. "
            "Run without --offline first.",
            file=sys.stderr,
        )
        sys.exit(1)

    GENERATED_OUT.parent.mkdir(parents=True, exist_ok=True)

    swagger2 = json.loads(SWAGGER_SNAPSHOT.read_bytes())
    oas3 = _patch_schema(_to_oas3(swagger2))

    # Use a fixed filename so the "filename:" comment in the generated header is stable
    # across runs (a random tmp name would break idempotency).
    tmp_dir = Path(tempfile.gettempdir())
    tmp_in_path = tmp_dir / "interacta_external_v2_oas3.json"
    tmp_in_path.write_text(json.dumps(oas3), encoding="utf-8")

    tmp_out_path = tmp_dir / "interacta_external_v2_codegen.py"

    try:
        cmd = [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(tmp_in_path),
            "--input-file-type",
            "openapi",
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--use-annotated",
            "--use-standard-collections",
            "--use-union-operator",
            "--target-python-version",
            "3.12",
            "--output",
            str(tmp_out_path),
            "--disable-timestamp",
        ]

        print("Running datamodel-code-generator …", flush=True)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("ERROR: datamodel-code-generator failed:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)
    finally:
        tmp_in_path.unlink(missing_ok=True)

    new_content = tmp_out_path.read_bytes()
    tmp_out_path.unlink(missing_ok=True)

    if GENERATED_OUT.exists() and GENERATED_OUT.read_bytes() == new_content:
        print("Generated file unchanged — nothing to write.", flush=True)
    else:
        GENERATED_OUT.write_bytes(new_content)
        print(f"Written → {GENERATED_OUT}", flush=True)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip the download; regenerate from the committed swagger.json snapshot.",
    )
    args = parser.parse_args()

    if not args.offline:
        download_swagger()

    run_codegen()
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
