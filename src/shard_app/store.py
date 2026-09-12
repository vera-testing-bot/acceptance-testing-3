"""Unified data access layer for the calculator app.

This module owns *all* application state. Components no longer hold their own
globals, serialize to localStorage by hand, or keep drifting copies. Instead
they read and write through :class:`Store`, which provides:

* **Typed accessors** — every field is declared with a :class:`Field` carrying
  a name, a Python type, a default, and the component that owns it.
* **Schema-versioned persistence** — the serialized blob carries a
  ``schema_version`` and a ``shape`` so old data can be detected and upgraded.
* **Migration support** — :meth:`Store.migrate` upgrades schema-less legacy
  blobs (the ones already sitting in real users' browsers) to the current
  schema before they are loaded.
* **Observability** — every write records a :class:`Transition` (who wrote,
  what field, old/new value, when) so the debug view can answer "where did
  this piece of state come from?".

The store is backend-agnostic: any object implementing ``read() -> str|None``
and ``write(str) -> None`` works. :class:`MemoryBackend` is the default;
:class:`FileBackend` is provided for real persistence.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 2
CURRENT_SHAPE = "calculator.v2"


@dataclass(frozen=True)
class Field:
    """A typed declaration of one piece of application state."""

    name: str
    type: type
    default: Any
    owner: str

    def validate(self, value: Any) -> Any:
        """Coerce ``value`` to this field's type, raising on impossible casts."""
        if value is None:
            return self.default
        try:
            return self.type(value)
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"field {self.name!r} expects {self.type.__name__}, got "
                f"{type(value).__name__}: {value!r}"
            ) from exc


@dataclass(frozen=True)
class Transition:
    """A single recorded write — the unit of the store's observability."""

    field: str
    old: Any
    new: Any
    writer: str
    timestamp: float


@dataclass
class Schema:
    """The set of fields the store owns at the current schema version."""

    fields: Mapping[str, Field]

    def defaults(self) -> dict[str, Any]:
        return {name: f.default for name, f in self.fields.items()}

    def coerce(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, f in self.fields.items():
            out[name] = f.validate(raw.get(name))
        return out


class MemoryBackend:
    """An in-memory backend that mimics a localStorage key/value slot."""

    def __init__(self, initial: str | None = None) -> None:
        self._value = initial

    def read(self) -> str | None:
        return self._value

    def write(self, payload: str) -> None:
        self._value = payload


class FileBackend:
    """A real persistence backend backed by a single JSON file."""

    def __init__(self, path: str) -> None:
        self._path = path

    def read(self) -> str | None:
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            return None

    def write(self, payload: str) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            fh.write(payload)


MigrationFn = Callable[[Mapping[str, Any]], dict[str, Any]]


def _migrate_v0_to_v1(blob: Mapping[str, Any]) -> dict[str, Any]:
    """Upgrade a schema-less blob (no ``schema_version``) to shape v1.

    The legacy calculator serialized display/history/settings as three separate
    localStorage entries that occasionally drifted. Here we accept any of the
    known legacy shapes and normalize them into the v1 field set.
    """
    out: dict[str, Any] = {
        "schema_version": 1,
        "shape": "calculator.v1",
        "display": "0",
        "history": [],
        "angle_mode": "deg",
        "precision": 6,
    }
    out["display"] = str(blob.get("display", blob.get("displayValue", "0")))
    raw_history = blob.get("history", blob.get("entries", []))
    out["history"] = list(raw_history) if isinstance(raw_history, Sequence) else []
    out["angle_mode"] = str(blob.get("angle_mode", blob.get("angleMode", "deg")))
    out["precision"] = int(blob.get("precision", blob.get("rounding", 6)))
    return out


def _migrate_v1_to_v2(blob: Mapping[str, Any]) -> dict[str, Any]:
    """Upgrade a v1 blob to the current v2 shape (adds ``last_writer``)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "shape": CURRENT_SHAPE,
        "display": str(blob.get("display", "0")),
        "history": list(blob.get("history", [])),
        "angle_mode": str(blob.get("angle_mode", "deg")),
        "precision": int(blob.get("precision", 6)),
        "last_writer": None,
    }


MIGRATIONS: dict[int, MigrationFn] = {
    0: _migrate_v0_to_v1,
    1: _migrate_v1_to_v2,
}


def migrate(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Run every migration from the blob's version up to :data:`SCHEMA_VERSION`."""
    version = int(raw.get("schema_version", 0))
    blob: dict[str, Any] = dict(raw)
    while version < SCHEMA_VERSION:
        blob = MIGRATIONS[version](blob)
        version = int(blob.get("schema_version", version))
    return blob


def default_schema() -> Schema:
    """The canonical field set for the calculator app at the current version."""
    fields = {
        "display": Field("display", str, "0", "calculator"),
        "history": Field("history", list, [], "history"),
        "angle_mode": Field("angle_mode", str, "deg", "settings"),
        "precision": Field("precision", int, 6, "settings"),
        "last_writer": Field("last_writer", str, "", "store"),
    }
    return Schema(fields)


class Store:
    """The single owner of all application state.

    Components call :meth:`get` / :meth:`set` with their ``writer`` identity;
    the store records the transition, validates the type, and persists the new
    blob through its backend. The history panel, settings, and calculator all
    read from this one object — there is no second copy to drift.
    """

    def __init__(
        self,
        backend: MemoryBackend | FileBackend | None = None,
        schema: Schema | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backend = backend if backend is not None else MemoryBackend()
        self._schema = schema if schema is not None else default_schema()
        self._clock = clock
        self._transitions: list[Transition] = []
        self._state: dict[str, Any] = self._load()

    # -- persistence ------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        raw = self._backend.read()
        if raw is None:
            return self._schema.defaults()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return self._schema.defaults()
        if not isinstance(parsed, Mapping):
            return self._schema.defaults()
        upgraded = migrate(parsed)
        return self._schema.coerce(upgraded)

    def _persist(self) -> None:
        blob = {"schema_version": SCHEMA_VERSION, "shape": CURRENT_SHAPE}
        blob.update(self._state)
        self._backend.write(json.dumps(blob))

    # -- typed accessors --------------------------------------------------

    def get(self, name: str) -> Any:
        if name not in self._schema.fields:
            raise KeyError(f"unknown field {name!r}")
        return self._state[name]

    def set(self, name: str, value: Any, writer: str) -> None:
        if name not in self._schema.fields:
            raise KeyError(f"unknown field {name!r}")
        coerced = self._schema.fields[name].validate(value)
        old = self._state.get(name)
        self._state[name] = coerced
        self._state["last_writer"] = writer
        self._transitions.append(Transition(name, old, coerced, writer, self._clock()))
        self._persist()

    # -- history as a view ------------------------------------------------

    def append_history(self, entry: str, writer: str) -> None:
        history = list(self._state["history"])
        history.append(entry)
        self.set("history", history, writer)

    def clear_history(self, writer: str) -> None:
        self.set("history", [], writer)

    # -- observability ----------------------------------------------------

    def transitions(self) -> Iterator[Transition]:
        yield from self._transitions

    def debug_view(self) -> dict[str, Any]:
        """A snapshot for the debug panel: state + recent transition log."""
        recent = [
            {
                "field": t.field,
                "old": t.old,
                "new": t.new,
                "writer": t.writer,
                "timestamp": t.timestamp,
            }
            for t in list(self._transitions)[-20:]
        ]
        return {"state": dict(self._state), "recent_transitions": recent}

    # -- introspection ----------------------------------------------------

    @property
    def schema_version(self) -> int:
        return SCHEMA_VERSION

    @property
    def shape(self) -> str:
        return CURRENT_SHAPE
