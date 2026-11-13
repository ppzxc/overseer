"""Checks the guarded PostgreSQL-to-SQLite migration helper."""

import importlib.util


def load_migration_module(root_dir):
    script = root_dir / "scripts" / "migrate-semaphore-postgres-to-sqlite.py"
    spec = importlib.util.spec_from_file_location("semaphore_migration", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ctrl_009_migration_tool_and_runbook(root_dir):
    """[CTRL-009] Migration helper and operational steps are deployed together."""
    script = root_dir / "scripts" / "migrate-semaphore-postgres-to-sqlite.py"
    guide = root_dir / "docs" / "control-plane" / "semaphore-postgres-to-sqlite.md"
    assert script.exists() and script.stat().st_mode & 0o111
    assert guide.exists()
    assert "task__output" in guide.read_text(encoding="utf-8")
    assert "SEMAPHORE_ACCESS_KEY_ENCRYPTION" in guide.read_text(encoding="utf-8")


def test_migration_checksum_is_order_independent(root_dir):
    migration = load_migration_module(root_dir)
    types = ["integer", "text"]
    first = migration.row_hashes([(1, "alpha"), (2, "beta")], types)
    second = migration.row_hashes([(2, "beta"), (1, "alpha")], types)
    assert first == second


def test_migration_normalizes_cross_database_values(root_dir):
    migration = load_migration_module(root_dir)
    assert migration.normalized(True, "boolean") == 1
    assert migration.normalized('{"b":2,"a":1}', "jsonb") == '{"a":1,"b":2}'
    assert migration.adapt_value({"b": 2, "a": 1}) == '{"a":1,"b":2}'
