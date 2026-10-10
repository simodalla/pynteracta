# SPDX-License-Identifier: Apache-2.0
"""Static checks on the Python code blocks in README.md and docs/**/*.md.

Blocks are never executed (they need a tenant). Each ```python block must:

1. compile;
2. import only existing ``pynteracta`` modules / names;
3. use only existing attributes when the attribute chain starts at an imported ``pynteracta``
   class or module (e.g. ``InteractaClient.from_service_account`` would fail here).

Instance attributes (``client.users``) are not checked. A block can opt out by placing
``<!-- snippet: skip -->`` on the line right before the opening fence.
"""

from __future__ import annotations

import ast
import importlib
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SKIP_MARKER = "<!-- snippet: skip -->"
_MIN_EXPECTED_SNIPPETS = 10
_FENCE_RE = re.compile(r"^```python[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True)
class Snippet:
    path: Path
    index: int
    source: str

    @property
    def label(self) -> str:
        return f"{self.path.relative_to(_ROOT)}#{self.index}"


def _collect() -> list[Snippet]:
    files = [_ROOT / "README.md", *sorted((_ROOT / "docs").rglob("*.md"))]
    out: list[Snippet] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for i, m in enumerate(_FENCE_RE.finditer(text), start=1):
            preceding = text[: m.start()].rstrip("\n").rsplit("\n", 1)[-1]
            if _SKIP_MARKER in preceding:
                continue
            out.append(Snippet(path, i, m.group(1)))
    return out


_SNIPPETS = _collect()


def _resolve_module(name: str, snippet: Snippet) -> object:
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        pytest.fail(f"{snippet.label}: cannot import module {name!r}: {exc}")


def _check_imports(tree: ast.AST, snippet: Snippet) -> dict[str, object]:
    """Verify pynteracta imports; return alias -> imported object for attribute checks."""
    bound: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "pynteracta":
                    bound[alias.asname or alias.name.split(".")[0]] = _resolve_module(
                        alias.name, snippet
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] != "pynteracta":
                continue
            mod = _resolve_module(node.module, snippet)
            for alias in node.names:
                if not hasattr(mod, alias.name):
                    try:
                        obj: object = importlib.import_module(f"{node.module}.{alias.name}")
                    except ImportError:
                        pytest.fail(f"{snippet.label}: {node.module!r} has no name {alias.name!r}")
                else:
                    obj = getattr(mod, alias.name)
                bound[alias.asname or alias.name] = obj
    return bound


def _check_static_attributes(tree: ast.AST, bound: dict[str, object], snippet: Snippet) -> None:
    """``Name.attr`` where Name is an imported pynteracta class/module must exist."""
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            continue
        base = bound.get(node.value.id)
        if base is None or not (isinstance(base, type) or hasattr(base, "__path__")):
            continue  # not a class/module we imported statically
        if not hasattr(base, node.attr):
            pytest.fail(
                f"{snippet.label}: {node.value.id}.{node.attr} does not exist "
                f"(line {node.lineno} of the snippet)"
            )


@pytest.mark.parametrize("snippet", _SNIPPETS, ids=[s.label for s in _SNIPPETS])
def test_doc_snippet_is_consistent_with_the_api(snippet: Snippet) -> None:
    try:
        tree = ast.parse(snippet.source, filename=snippet.label)
    except SyntaxError as exc:
        pytest.fail(f"{snippet.label}: syntax error: {exc}")
    bound = _check_imports(tree, snippet)
    _check_static_attributes(tree, bound, snippet)


def test_snippets_were_collected() -> None:
    assert len(_SNIPPETS) > _MIN_EXPECTED_SNIPPETS, "docs snippet collection looks broken"


# criterio: 01-C11
def test_logging_page_states_redaction_guarantees() -> None:
    """La pagina Audit Logging dichiara le garanzie di redazione di cookie e header per nome."""
    text = (_ROOT / "docs" / "logging.md").read_text(encoding="utf-8")
    guarantees = text.split("## Redaction guarantees", 1)[1].split("\n## ", 1)[0]
    for needle in ("Proxy-Authorization", "Set-Cookie", "api-key"):
        assert needle in guarantees, f"'{needle}' missing from the redaction guarantees"
    example = text.split("## Log format", 1)[1].split("\n## ", 1)[0]
    assert "interacta_auth_refresh_token=***REDACTED***" in example


# criterio: 02-C15
def test_tasks_pages_document_write_commands() -> None:
    """Le pagine CLI e API documentano le scritture dei task e l'exit code 9."""
    cli = (_ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
    for needle in ("tasks create", "tasks edit", "tasks delete", "--json", "--occ-token", "--yes"):
        assert needle in cli, f"'{needle}' missing from docs/cli.md"
    assert "| 9 |" in cli, "exit code 9 missing from the exit-code table in docs/cli.md"
    api = (_ROOT / "docs" / "api" / "tasks.md").read_text(encoding="utf-8")
    for needle in ("create(", "edit(", "delete(", "TaskWriteResult", "occ_token", "expiration"):
        assert needle in api, f"'{needle}' missing from docs/api/tasks.md"


_POST_WRITE_COMMANDS = (
    "posts create",
    "posts edit ",
    "posts edit-custom-data",
    "posts copy",
    "posts edit-watchers",
    "posts delete",
    "posts mark-erasable",
    "posts comment",
    "posts get-for-create",
    "posts get-for-edit",
    "posts get-for-copy",
    "posts workflow-screen",
    "posts workflow-execute",
    "posts workflow-edit-screen",
)


# criterio: 03-C30
def test_posts_pages_document_write_commands() -> None:
    """Le pagine CLI, API, home e README documentano le scritture dei post."""
    cli = (_ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
    for needle in (*_POST_WRITE_COMMANDS, "--custom-data", "--screen-data", "--screen-occ-token"):
        assert needle in cli, f"'{needle}' missing from docs/cli.md"
    api = (_ROOT / "docs" / "api" / "posts.md").read_text(encoding="utf-8")
    for needle in (
        "create(",
        "edit(",
        "copy(",
        "add_comment(",
        "execute_workflow_operation(",
        "PostWriteResult",
        "occ_token",
        "get_for_edit",
        "scheduled_publication",
    ):
        assert needle in api, f"'{needle}' missing from docs/api/posts.md"
    for page in (_ROOT / "docs" / "index.md", _ROOT / "README.md"):
        text = page.read_text(encoding="utf-8")
        write_lines = [line for line in text.splitlines() if "Write operations" in line]
        assert write_lines, f"no 'Write operations' line in {page.name}"
        paragraph = text[text.index(write_lines[0]) :].split("\n- ")[0]
        assert "posts" in paragraph, f"posts missing from the write operations of {page.name}"


# criterio: 03-C37
def test_posts_pages_document_references_and_replacement() -> None:
    """Le pagine dicono che edit sostituisce il post, che i riferimenti si scrivono come id e
    che i valori nuovi dei campi delta sono Quill delta."""
    api = (_ROOT / "docs" / "api" / "posts.md").read_text(encoding="utf-8")
    for needle in ("replacement", "as ids", "REQUIRED_FIELD"):
        assert needle in api, f"'{needle}' missing from docs/api/posts.md"
    cli = (_ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
    for needle in ("as ids", "Quill delta", "deltaAreaFormat"):
        assert needle in cli, f"'{needle}' missing from docs/cli.md"
