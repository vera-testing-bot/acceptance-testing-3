"""Characterization tests for the unified store and the components on top of it.

These pin the current behavior of the new unified data access layer and the
calculator/history/settings subsystems that moved onto it. They also cover the
schema-versioned persistence and migration path for the schema-less blobs that
already sit in real users' browsers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shard_app import (
    SCHEMA_VERSION,
    Calculator,
    FileBackend,
    HistoryPanel,
    MemoryBackend,
    Settings,
    Store,
    add,
    is_palindrome,
    migrate,
)
from shard_app.store import CURRENT_SHAPE, default_schema

# -- legacy seed test (kept green) -----------------------------------------


def test_add() -> None:
    assert add(2, 3) == 5


# -- is_palindrome helper --------------------------------------------------


def test_is_palindrome_true_for_ignoring_case_and_non_alnum() -> None:
    assert is_palindrome("A man, a plan, a canal: Panama") is True


def test_is_palindrome_false_for_non_palindrome() -> None:
    assert is_palindrome("hello") is False


# -- store: typed accessors ------------------------------------------------


def test_store_starts_with_defaults() -> None:
    store = Store()
    assert store.get("display") == "0"
    assert store.get("history") == []
    assert store.get("angle_mode") == "deg"
    assert store.get("precision") == 6
    assert store.get("last_writer") == ""


def test_store_set_records_writer_and_persists() -> None:
    backend = MemoryBackend()
    store = Store(backend=backend)
    store.set("display", "42", "calculator")
    assert store.get("display") == "42"
    assert store.get("last_writer") == "calculator"
    assert backend.read() is not None
    import json

    blob = json.loads(backend.read())
    assert blob["schema_version"] == SCHEMA_VERSION
    assert blob["shape"] == CURRENT_SHAPE
    assert blob["display"] == "42"


def test_store_rejects_unknown_field() -> None:
    store = Store()
    raised = False
    try:
        store.get("nope")
    except KeyError:
        raised = True
    assert raised
    raised = False
    try:
        store.set("nope", 1, "x")
    except KeyError:
        raised = True
    assert raised


def test_store_coerces_types() -> None:
    store = Store()
    store.set("precision", "8", "settings")
    assert store.get("precision") == 8
    assert isinstance(store.get("precision"), int)


def test_store_rejects_bad_type() -> None:
    store = Store()
    raised = False
    try:
        store.set("precision", "not-a-number", "settings")
    except TypeError:
        raised = True
    assert raised


# -- store: schema-versioned persistence ----------------------------------


def test_store_round_trips_through_file_backend(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    backend = FileBackend(str(path))
    store = Store(backend=backend)
    store.set("display", "12", "calculator")
    store.append_history("12 = 12", "calculator")
    store.set("angle_mode", "rad", "settings")

    reopened = Store(backend=backend)
    assert reopened.get("display") == "12"
    assert reopened.get("history") == ["12 = 12"]
    assert reopened.get("angle_mode") == "rad"


def test_store_reload_preserves_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    backend = FileBackend(str(path))
    store = Store(backend=backend)
    store.set("display", "9", "calculator")
    import json

    blob = json.loads(path.read_text())
    assert blob["schema_version"] == SCHEMA_VERSION


# -- store: migration ------------------------------------------------------


def test_migrate_schemaless_legacy_blob() -> None:
    legacy = {
        "displayValue": "77",
        "entries": ["1+1 = 2"],
        "angleMode": "rad",
        "rounding": 4,
    }
    upgraded = migrate(legacy)
    assert upgraded["schema_version"] == SCHEMA_VERSION
    assert upgraded["shape"] == CURRENT_SHAPE
    assert upgraded["display"] == "77"
    assert upgraded["history"] == ["1+1 = 2"]
    assert upgraded["angle_mode"] == "rad"
    assert upgraded["precision"] == 4


def test_migrate_v1_blob_adds_last_writer() -> None:
    v1 = {
        "schema_version": 1,
        "shape": "calculator.v1",
        "display": "5",
        "history": ["5 = 5"],
        "angle_mode": "deg",
        "precision": 6,
    }
    upgraded = migrate(v1)
    assert upgraded["schema_version"] == SCHEMA_VERSION
    assert upgraded["shape"] == CURRENT_SHAPE
    assert upgraded["display"] == "5"
    assert upgraded["history"] == ["5 = 5"]
    assert "last_writer" in upgraded


def test_store_loads_schemaless_blob_via_migration() -> None:
    import json

    legacy = {"displayValue": "31", "entries": [], "angleMode": "deg", "rounding": 2}
    backend = MemoryBackend(initial=json.dumps(legacy))
    store = Store(backend=backend)
    assert store.get("display") == "31"
    assert store.get("precision") == 2
    assert store.schema_version == SCHEMA_VERSION


def test_store_loads_v1_blob_via_migration() -> None:
    import json

    v1 = {
        "schema_version": 1,
        "shape": "calculator.v1",
        "display": "8",
        "history": ["8 = 8"],
        "angle_mode": "rad",
        "precision": 3,
    }
    backend = MemoryBackend(initial=json.dumps(v1))
    store = Store(backend=backend)
    assert store.get("display") == "8"
    assert store.get("history") == ["8 = 8"]
    assert store.get("angle_mode") == "rad"
    assert store.get("precision") == 3


def test_store_recover_from_corrupt_blob() -> None:
    backend = MemoryBackend(initial="{not json")
    store = Store(backend=backend)
    assert store.get("display") == "0"


# -- store: observability / debug view ------------------------------------


def test_transitions_record_writer_and_values() -> None:
    store = Store()
    store.set("display", "1", "calculator")
    store.set("display", "2", "calculator")
    transitions = list(store.transitions())
    assert len(transitions) == 2
    assert transitions[0].field == "display"
    assert transitions[0].writer == "calculator"
    assert transitions[0].old == "0"
    assert transitions[0].new == "1"
    assert transitions[1].old == "1"
    assert transitions[1].new == "2"


def test_debug_view_shows_state_and_recent_transitions() -> None:
    store = Store()
    store.set("display", "5", "calculator")
    store.append_history("5 = 5", "calculator")
    view = store.debug_view()
    assert view["state"]["display"] == "5"
    assert view["state"]["history"] == ["5 = 5"]
    assert len(view["recent_transitions"]) == 2
    assert view["recent_transitions"][0]["writer"] == "calculator"
    assert view["recent_transitions"][-1]["field"] == "history"


def test_debug_view_caps_recent_transitions() -> None:
    store = Store()
    for i in range(30):
        store.set("display", str(i), "calculator")
    view = store.debug_view()
    assert len(view["recent_transitions"]) == 20
    assert view["recent_transitions"][-1]["new"] == "29"


# -- calculator component --------------------------------------------------


def test_calculator_input_and_display() -> None:
    store = Store()
    calc = Calculator(store)
    calc.input_digit("1")
    calc.input_digit("2")
    assert calc.display == "12"
    calc.input_decimal()
    calc.input_digit("5")
    assert calc.display == "12.5"


def test_calculator_clear_resets_display_only() -> None:
    store = Store()
    calc = Calculator(store)
    calc.input_digit("7")
    calc.evaluate()
    assert store.get("history") == ["7 = 7.0"]
    calc.clear()
    assert calc.display == "0"
    assert store.get("history") == ["7 = 7.0"]


def test_calculator_evaluate_appends_history() -> None:
    store = Store()
    calc = Calculator(store)
    calc.input_digit("6")
    assert calc.evaluate() == 6.0
    assert calc.display == "6.0"
    assert store.get("history") == ["6 = 6.0"]


def test_calculator_precision_follows_settings() -> None:
    store = Store()
    Settings(store).precision = 2
    calc = Calculator(store)
    calc._store.set("display", "10/3", "calculator")
    result = calc.evaluate()
    assert result == 3.33
    assert calc.display == "3.33"


# -- history panel is a view over the store --------------------------------


def test_history_panel_reads_single_source() -> None:
    store = Store()
    calc = Calculator(store)
    calc.input_digit("1")
    calc.evaluate()
    panel = HistoryPanel(store)
    assert panel.entries() == ["1 = 1.0"]
    calc.clear()
    calc.input_digit("2")
    calc.evaluate()
    assert panel.entries() == ["1 = 1.0", "2 = 2.0"]


def test_history_panel_clear_writes_through_store() -> None:
    store = Store()
    calc = Calculator(store)
    calc.input_digit("1")
    calc.evaluate()
    panel = HistoryPanel(store)
    panel.clear()
    assert panel.entries() == []
    assert store.get("history") == []
    transitions = [t for t in store.transitions() if t.field == "history"]
    assert transitions[-1].writer == "history"


# -- settings subsystem ----------------------------------------------------


def test_settings_angle_mode_validation() -> None:
    store = Store()
    settings = Settings(store)
    assert settings.angle_mode == "deg"
    settings.angle_mode = "rad"
    assert settings.angle_mode == "rad"
    raised = False
    try:
        settings.angle_mode = "gradians"
    except ValueError:
        raised = True
    assert raised


def test_settings_precision_validation() -> None:
    store = Store()
    settings = Settings(store)
    raised = False
    try:
        settings.precision = -1
    except ValueError:
        raised = True
    assert raised


# -- schema introspection --------------------------------------------------


def test_default_schema_lists_all_owned_fields() -> None:
    schema = default_schema()
    assert set(schema.fields) == {
        "display",
        "history",
        "angle_mode",
        "precision",
        "last_writer",
    }
    for name, f in schema.fields.items():
        assert f.name == name
        assert f.owner in {"calculator", "history", "settings", "store"}
