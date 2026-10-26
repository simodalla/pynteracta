# SPDX-License-Identifier: Apache-2.0
"""Structured logging helpers and redaction utilities.

The library never calls ``structlog.configure()`` at import time.
Call :func:`setup_default_logging` explicitly from a CLI entry-point or test
harness when you want opinionated defaults wired up.
"""

from __future__ import annotations

import logging
import logging.handlers
import re
import sys
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

import structlog

_REDACTED = "***REDACTED***"

# Matches the leading two Base64-encoded JSON header segments of a JWT.
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9+/._\-]{10,}")

# Body fields whose *key* (case-insensitive) should always be redacted. ``signature`` e
# ``policy`` sono i campi della policy firmata dello storage (spec 04).
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)token|password|secret|privatekey|assertion|jwt|signature|policy"
)

# Chiavi dei body che contengono ``token`` ma non sono segreti: i token di concorrenza
# ottimistica (``occToken`` e varianti), contatori di versione dell'entità che non autenticano
# nessuno. Restano in chiaro perché l'audit delle scritture deve mostrare quale token è stato letto
# e quale inviato. Confronto per nome esatto, in minuscolo: ogni altra chiave con ``token`` resta
# redatta (in dubbio si redige, spec 07).
_OCC_TOKEN_KEYS = frozenset(
    {
        "occtoken",
        "nextocctoken",
        "screenocctoken",
        "nextscreenocctoken",
        "occ_token",
        "next_occ_token",
        "screen_occ_token",
        "next_screen_occ_token",
    }
)

# Parametro di query di un URL il cui nome contiene una parola sensibile (``Signature`` dei link
# firmati, ``access_token``, ``apiKey``…): resta il nome, il valore è redatto. Il nome deve seguire
# ``?`` o ``&``, così il testo ordinario non è toccato (spec 04).
_SENSITIVE_QUERY_RE = re.compile(
    r"(?i)([?&][^&=#\s]*(?:signature|token|secret|password|key)[^&=#\s]*=)([^&#\s\"']*)"
)

# Header il cui intero valore è sempre redatto, per nome (confronto in minuscolo): la lista fissa
# degli header di autenticazione standard più un pattern sul nome, simmetrico a quello delle chiavi
# dei body. ``api[-_]?key`` copre ``X-Api-Key`` e ``x_api_key``.
_SENSITIVE_HEADER_NAMES = frozenset({"authorization", "proxy-authorization"})
_SENSITIVE_HEADER_RE = re.compile(r"(?i)token|secret|password|api[-_]?key")

# Header cookie: il valore di ogni cookie è redatto, nome e attributi restano.
_COOKIE_HEADER_NAMES = frozenset({"cookie", "set-cookie"})
# Attributi di ``Set-Cookie`` (RFC 6265 più Partitioned e Priority), in minuscolo: una coppia
# ``nome=valore`` con uno di questi nomi, preceduta da ``;``, è un attributo e non si tocca.
_COOKIE_ATTRIBUTES = frozenset(
    {
        "expires",
        "max-age",
        "domain",
        "path",
        "samesite",
        "secure",
        "httponly",
        "partitioned",
        "priority",
    }
)
# Una coppia ``nome=valore`` con il separatore che la precede: l'inizio del valore, ``,`` (così
# httpx unisce più ``Set-Cookie``: ogni coppia dopo una virgola è un nuovo cookie) o ``;``.
# Un frammento senza ``=`` (la parte dopo la virgola di ``Expires=Thu, 02 Jul …``) non è una coppia.
_COOKIE_PAIR_RE = re.compile(r"(^|[;,])(\s*)([^;,=\s]+)=([^;,]*)")

_AUDIT_LOGGER_NAME = "pynteracta.audit"
_AUDIT_RAW_WARNED = False


# ---------------------------------------------------------------------------
# Public redaction helpers (used by transport.py and tests)
# ---------------------------------------------------------------------------


def redact_string(value: str) -> str:
    """Redige una stringa: i valori dei parametri di query sensibili, poi i JWT.

    I parametri di query il cui nome contiene ``signature``, ``token``, ``secret``, ``password``
    o ``key`` perdono il valore (nome e altri parametri restano); ogni sottostringa a forma di
    JWT diventa ``***REDACTED***``.
    """
    value = _SENSITIVE_QUERY_RE.sub(rf"\1{_REDACTED}", value)
    return _JWT_RE.sub(_REDACTED, value)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of *headers* with sensitive values blanked out.

    Gli header ``Authorization`` e ``Proxy-Authorization``, e quelli il cui nome contiene
    ``token``, ``secret``, ``password`` o ``api-key``, perdono l'intero valore qualunque sia la
    sua forma. Ogni altro valore passa da :func:`redact_string`, che sostituisce i JWT.
    """
    result: dict[str, str] = {}
    for k, v in headers.items():
        name = k.lower()
        if name in _SENSITIVE_HEADER_NAMES or _SENSITIVE_HEADER_RE.search(name):
            result[k] = _REDACTED
        elif name in _COOKIE_HEADER_NAMES:
            result[k] = _redact_cookie_header(name, v)
        else:
            result[k] = redact_string(v)
    return result


def _redact_cookie_header(name: str, value: str) -> str:
    """Redige il valore di ogni cookie di un header ``Cookie`` o ``Set-Cookie``.

    ``name`` è il nome dell'header in minuscolo. In ``Cookie`` ogni coppia è un cookie; in
    ``Set-Cookie`` lo è la coppia all'inizio o dopo una virgola, e quella dopo ``;`` il cui nome
    non è un attributo noto. Un valore senza ``=`` o con virgolette non si lascia analizzare con
    certezza: in dubbio si redige per intero.
    """
    if "=" not in value or '"' in value:
        return _REDACTED

    def _sub(match: re.Match[str]) -> str:
        sep, ws, key = match.group(1), match.group(2), match.group(3)
        is_cookie = name == "cookie" or sep != ";" or key.lower() not in _COOKIE_ATTRIBUTES
        return f"{sep}{ws}{key}={_REDACTED}" if is_cookie else match.group(0)

    return _COOKIE_PAIR_RE.sub(_sub, value)


def _is_sensitive_key(name: str) -> bool:
    """Dice se il valore della chiave ``name`` di un body va redatto.

    Le chiavi dei token di concorrenza ottimistica (``_OCC_TOKEN_KEYS``) non sono sensibili;
    ogni altra chiave lo è se il nome contiene una parola di ``_SENSITIVE_KEY_RE``.
    """
    if name.lower() in _OCC_TOKEN_KEYS:
        return False
    return _SENSITIVE_KEY_RE.search(name) is not None


def redact_body(body: Any) -> Any:
    """Redige ricorsivamente le chiavi sensibili di un body; il resto passa invariato.

    Percorre ``dict`` e ``list`` annidati: il valore di una chiave sensibile diventa
    ``***REDACTED***``, le stringhe passano da :func:`redact_string`. I token di concorrenza
    ottimistica (``occToken``, ``nextOccToken``, ``screenOccToken``, ``nextScreenOccToken`` e le
    grafie snake_case) restano in chiaro: sono contatori di versione, non segreti.
    """
    if isinstance(body, dict):
        return {k: _REDACTED if _is_sensitive_key(k) else redact_body(v) for k, v in body.items()}
    if isinstance(body, list):
        return [redact_body(item) for item in body]
    if isinstance(body, str):
        return redact_string(body)
    return body


# ---------------------------------------------------------------------------
# structlog processor
# ---------------------------------------------------------------------------


def redaction_processor(
    logger: Any,
    method: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """structlog processor — redact JWTs and Authorization from every log event.

    Safe to include in the processor chain even when no sensitive data is
    present; it is a no-op for values that do not match.
    """
    _ = logger  # unused but required by the structlog processor signature
    _ = method  # unused but required by the structlog processor signature
    for key in list(event_dict.keys()):
        value = event_dict[key]
        if key == "headers" and isinstance(value, Mapping):
            event_dict[key] = redact_headers(dict(value))
        elif key == "body":
            event_dict[key] = redact_body(value)
        elif isinstance(value, str):
            if key.lower() == "authorization":
                event_dict[key] = _REDACTED
            else:
                event_dict[key] = redact_string(value)
    return event_dict


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def get_logger(name: str = "pynteracta") -> Any:
    """Return a named structlog logger."""
    return structlog.get_logger(name)


# ---------------------------------------------------------------------------
# Audit file handler builder
# ---------------------------------------------------------------------------


def build_audit_file_handler(
    path: Path,
    *,
    max_bytes: int = 10_000_000,
    backup_count: int = 5,
) -> logging.Handler:
    """Return a :class:`~logging.handlers.RotatingFileHandler` for JSON-lines audit output.

    The handler uses the same structlog redaction processor chain so tokens are
    never written to disk in clear text.
    """
    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.EventRenamer("event"),
        redaction_processor,
    ]
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler


# ---------------------------------------------------------------------------
# Opt-in setup helper
# ---------------------------------------------------------------------------


_MANAGED_ATTR = "_pynteracta_managed"


def _mark_managed(handler: logging.Handler) -> logging.Handler:
    """Marca un handler come installato da :func:`setup_default_logging`."""
    setattr(handler, _MANAGED_ATTR, True)
    return handler


def _remove_managed_handlers(logger: logging.Logger) -> None:
    """Rimuove e chiude gli handler installati da una chiamata precedente.

    Gli handler aggiunti dall'utente, privi del marcatore, restano al loro posto.
    """
    for handler in list(logger.handlers):
        if getattr(handler, _MANAGED_ATTR, False):
            logger.removeHandler(handler)
            handler.close()


def setup_default_logging(  # noqa: PLR0913
    level: str = "INFO",
    *,
    json: bool | None = None,
    audit: bool = False,
    audit_file: Path | None = None,
    audit_max_bytes: int = 10_000_000,
    audit_backups: int = 5,
    audit_bodies: bool = False,
    audit_raw: bool = False,
) -> None:
    """Configure structlog with opinionated defaults.

    This is an opt-in helper; the library never calls it implicitly.

    La funzione è idempotente: una nuova chiamata sostituisce gli handler installati dalla
    precedente (la CLI la invoca due volte per comando) invece di accumularli, che farebbe
    uscire ogni riga di log più volte. Gli handler aggiunti dall'utente non vengono toccati.

    Args:
        level: Log level string (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
        json: Force JSON output when ``True``, console output when ``False``.
            Defaults to ``True`` when stdout is not a TTY.
        audit: Enable the dedicated ``pynteracta.audit`` logger.
        audit_file: If set, attach a :class:`~logging.handlers.RotatingFileHandler`
            writing JSON-lines to this path.  Implies ``audit=True``.
        audit_max_bytes: Max bytes per audit log file before rotation (default 10 MB).
        audit_backups: Number of rotated backup files to keep (default 5).
        audit_bodies: Whether audit events should include request/response bodies.
            Bodies are **never** captured unless this is ``True``.
        audit_raw: If ``True``, bypass redaction on the audit channel and emit a
            loud warning.  Use only for deep debugging; never in production.
    """
    global _AUDIT_RAW_WARNED  # noqa: PLW0603

    use_json = json if json is not None else not sys.stdout.isatty()

    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.EventRenamer("event"),
        redaction_processor,
    ]

    if use_json:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger("pynteracta")
    _remove_managed_handlers(root)
    root.addHandler(_mark_managed(handler))
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # ------------------------------------------------------------------
    # Audit logger
    # ------------------------------------------------------------------
    enable_audit = audit or audit_file is not None
    audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
    _remove_managed_handlers(audit_logger)
    if enable_audit:
        audit_logger.setLevel(logging.DEBUG)
        audit_logger.propagate = False  # don't double-emit on root pynteracta logger

        if audit_raw:
            # L'avviso esce una sola volta per processo; l'handler raw si installa a ogni chiamata.
            warn_raw = not _AUDIT_RAW_WARNED
            _AUDIT_RAW_WARNED = True
            audit_processors_raw: list[Any] = [
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.EventRenamer("event"),
                # redaction_processor intentionally omitted
            ]
            raw_formatter = structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=audit_processors_raw,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(),
                ],
            )
            raw_console_handler = logging.StreamHandler()
            raw_console_handler.setFormatter(raw_formatter)
            audit_logger.addHandler(_mark_managed(raw_console_handler))
            if warn_raw:
                logging.getLogger("pynteracta").warning(
                    "audit.redaction_disabled: --audit-raw is active — "
                    "raw tokens and sensitive data MAY appear in audit output. "
                    "Never use this in production."
                )
        else:
            audit_console_handler = logging.StreamHandler()
            audit_console_formatter = structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared_processors,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    renderer,
                ],
            )
            audit_console_handler.setFormatter(audit_console_formatter)
            audit_logger.addHandler(_mark_managed(audit_console_handler))

        if audit_file is not None:
            file_handler = build_audit_file_handler(
                audit_file,
                max_bytes=audit_max_bytes,
                backup_count=audit_backups,
            )
            if audit_raw:
                # Apply raw (no-redaction) formatter to file handler too
                raw_file_processors: list[Any] = [
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.add_logger_name,
                    structlog.processors.TimeStamper(fmt="iso", utc=True),
                    structlog.processors.EventRenamer("event"),
                ]
                raw_file_formatter = structlog.stdlib.ProcessorFormatter(
                    foreign_pre_chain=raw_file_processors,
                    processors=[
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.JSONRenderer(),
                    ],
                )
                file_handler.setFormatter(raw_file_formatter)
            audit_logger.addHandler(_mark_managed(file_handler))
