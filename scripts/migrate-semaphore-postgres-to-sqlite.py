#!/usr/bin/env python3
"""Copy a stopped Semaphore PostgreSQL database into an initialized SQLite DB.

The destination schema must have been created by the same Semaphore image as
the source. The script deliberately refuses to guess across schema changes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import decimal
import hashlib
import ipaddress
import json
import os
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any


MIGRATION_TABLES = {"migration", "migrations"}
CHUNK_SIZE = 1000
SUPPORTED_PG_TYPES = {
    "smallint", "integer", "bigint", "real", "double precision", "numeric", "decimal",
    "boolean", "character varying", "character", "text", "json", "jsonb", "bytea",
    "date", "time without time zone", "time with time zone", "timestamp without time zone",
    "timestamp with time zone", "uuid", "inet", "cidr",
}


def quote_sqlite(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def quote_postgres(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def json_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def adapt_value(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat(sep=" ") if isinstance(value, dt.datetime) else value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (dict, list)):
        return json_value(value)
    if isinstance(value, (memoryview, bytearray)):
        return bytes(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address, ipaddress.IPv4Network, ipaddress.IPv6Network)):
        return str(value)
    return value


def normalized(value: Any, pg_type: str) -> Any:
    """Represent PostgreSQL and SQLite values consistently for table hashes."""
    type_name = pg_type.lower()
    if value is None:
        return None
    if type_name in {"json", "jsonb"}:
        if isinstance(value, str):
            value = json.loads(value)
        return json_value(value)
    if type_name in {"bool", "boolean"}:
        return int(value)
    if type_name in {"bytea", "blob", "binary", "varbinary"}:
        return bytes(value).hex()
    if type_name in {"timestamp", "timestamptz", "timestamp without time zone", "timestamp with time zone", "date", "time", "time without time zone", "time with time zone"}:
        if isinstance(value, (dt.datetime, dt.date, dt.time)):
            return adapt_value(value)
        return str(value)
    if type_name in {"uuid"}:
        return str(value)
    if type_name in {"inet", "cidr"}:
        return str(value)
    if type_name in {"numeric", "decimal"}:
        return decimal.Decimal(str(value)).normalize().to_eng_string()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return value


def row_hashes(rows, types: list[str]) -> tuple[int, str]:
    hashes = []
    count = 0
    for row in rows:
        normalized_row = [normalized(value, types[index]) for index, value in enumerate(row)]
        hashes.append(hashlib.sha256(json_value(normalized_row).encode("utf-8")).digest())
        count += 1
    digest = hashlib.sha256()
    for row_digest in sorted(hashes):
        digest.update(row_digest)
    return count, digest.hexdigest()


def load_pg_schema(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT table_name, column_name, data_type, udt_name, ordinal_position
                 FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position"""
        )
        schema: dict[str, list[tuple[str, str]]] = {}
        for table, column, data_type, udt_name, _ in cursor.fetchall():
            schema.setdefault(table, []).append((column, udt_name if data_type == "USER-DEFINED" else data_type))
    return schema


def load_sqlite_schema(connection):
    names = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    schema = {}
    for table in names:
        schema[table] = [(row[1], row[2]) for row in connection.execute(f"PRAGMA table_info({quote_sqlite(table)})")]
    return schema


def sqlite_affinity(declared_type: str) -> str:
    value = declared_type.upper()
    if "INT" in value:
        return "INTEGER"
    if any(token in value for token in ("CHAR", "CLOB", "TEXT", "JSON")):
        return "TEXT"
    if "BLOB" in value or not value:
        return "BLOB"
    if any(token in value for token in ("REAL", "FLOA", "DOUB")):
        return "REAL"
    return "NUMERIC"


def expected_sqlite_affinity(pg_type: str) -> str:
    value = pg_type.lower()
    if value in {"smallint", "integer", "bigint"}:
        return "INTEGER"
    if value in {"real", "double precision"}:
        return "REAL"
    if value == "bytea":
        return "BLOB"
    if value in {"numeric", "decimal"}:
        return "NUMERIC"
    return "TEXT"


def compatible_sqlite_affinities(pg_type: str) -> set[str]:
    value = pg_type.lower()
    if value == "boolean":
        return {"INTEGER", "NUMERIC"}
    if value in {"date", "time without time zone", "time with time zone", "timestamp without time zone", "timestamp with time zone"}:
        return {"TEXT", "NUMERIC"}
    return {expected_sqlite_affinity(value)}


def primary_key_columns(pg_connection, table: str) -> list[str]:
    with pg_connection.cursor() as cursor:
        cursor.execute(
            """SELECT a.attname
                 FROM pg_index i
                 JOIN pg_class t ON t.oid = i.indrelid
                 JOIN pg_namespace n ON n.oid = t.relnamespace
                 JOIN unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) ON true
                 JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
                WHERE n.nspname = 'public' AND t.relname = %s AND i.indisprimary
                ORDER BY k.ord""",
            (table,),
        )
        return [row[0] for row in cursor.fetchall()]


def copy_table(pg_connection, sqlite_connection, table: str, columns: list[tuple[str, str]]) -> dict[str, Any]:
    column_names = [column for column, _ in columns]
    pg_columns = ", ".join(quote_postgres(column) for column in column_names)
    sqlite_columns = ", ".join(quote_sqlite(column) for column in column_names)
    placeholders = ", ".join("?" for _ in column_names)
    pg_order = primary_key_columns(pg_connection, table)
    order_clause = " ORDER BY " + ", ".join(quote_postgres(col) for col in pg_order) if pg_order else ""

    cursor_name = "overseer_migrate_" + hashlib.sha1(table.encode()).hexdigest()[:12]
    with pg_connection.cursor(name=cursor_name) as source:
        source.itersize = CHUNK_SIZE
        source.execute(f"SELECT {pg_columns} FROM public.{quote_postgres(table)}{order_clause}")
        insert = f"INSERT INTO {quote_sqlite(table)} ({sqlite_columns}) VALUES ({placeholders})"
        count = 0
        hashes = []
        types = [type_name for _, type_name in columns]
        while batch := source.fetchmany(CHUNK_SIZE):
            adapted = [tuple(adapt_value(value) for value in row) for row in batch]
            sqlite_connection.executemany(insert, adapted)
            for row in batch:
                normalized_row = [normalized(value, types[index]) for index, value in enumerate(row)]
                hashes.append(hashlib.sha256(json_value(normalized_row).encode("utf-8")).digest())
                count += 1
    digest = hashlib.sha256()
    for row_digest in sorted(hashes):
        digest.update(row_digest)
    return {"rows": count, "sha256": digest.hexdigest()}


def update_sequences(pg_connection, sqlite_connection, pg_schema: dict[str, list[tuple[str, str]]]):
    has_sqlite_sequence = bool(sqlite_connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'"
    ).fetchone())

    with pg_connection.cursor() as cursor:
        cursor.execute(
            """SELECT t.relname, a.attname, s.relname
                 FROM pg_class s
                 JOIN pg_namespace sn ON sn.oid = s.relnamespace
                 JOIN pg_depend d ON d.objid = s.oid AND d.deptype IN ('a', 'i')
                 JOIN pg_class t ON t.oid = d.refobjid
                 JOIN pg_namespace tn ON tn.oid = t.relnamespace
                 JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
                WHERE s.relkind = 'S' AND sn.nspname = 'public' AND tn.nspname = 'public'
                ORDER BY t.relname, a.attname"""
        )
        sequences = cursor.fetchall()

    results = []
    for table, column, sequence in sequences:
        if table not in pg_schema or table in MIGRATION_TABLES:
            continue
        with pg_connection.cursor() as cursor:
            cursor.execute(f"SELECT last_value, is_called FROM public.{quote_postgres(sequence)}")
            last_value, is_called = cursor.fetchone()
        row = sqlite_connection.execute(
            "SELECT seq FROM sqlite_sequence WHERE name = ?", (table,)
        ).fetchone() if has_sqlite_sequence else None
        maximum = sqlite_connection.execute(
            f"SELECT MAX({quote_sqlite(column)}) FROM {quote_sqlite(table)}"
        ).fetchone()[0]
        table_ddl = sqlite_connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?", (table,)
        ).fetchone()[0]
        autoincrement = bool(table_ddl and "AUTOINCREMENT" in table_ddl.upper())
        expected_next = int(last_value) + 1 if is_called else int(last_value)
        if autoincrement and has_sqlite_sequence:
            sqlite_sequence = max(0, expected_next - 1)
            if row is None:
                sqlite_connection.execute(
                    "INSERT INTO sqlite_sequence(name, seq) VALUES (?, ?)", (table, sqlite_sequence)
                )
            else:
                sqlite_connection.execute(
                    "UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (sqlite_sequence, table)
                )
        else:
            sqlite_sequence = None
            sqlite_next = int(maximum) + 1 if maximum is not None else 1
            if sqlite_next != expected_next:
                raise RuntimeError(
                    f"Cannot preserve sequence for {table}.{column}: PostgreSQL next ID is {expected_next}, SQLite rowid allocation would be {sqlite_next}"
                )
        if maximum is not None and sqlite_sequence is not None and sqlite_sequence < int(maximum):
            raise RuntimeError(f"SQLite sequence for {table}.{column} is below its maximum key")
        results.append({"table": table, "column": column, "postgres_last_value": last_value, "postgres_next_id": expected_next, "sqlite_sequence": sqlite_sequence, "max_imported_key": maximum})
    return results


def verify_sqlite(pg_connection, sqlite_connection, pg_schema, target_schema):
    summary = {}
    for table, columns in pg_schema.items():
        if table in MIGRATION_TABLES:
            continue
        names = [column for column, _ in columns]
        order = primary_key_columns(pg_connection, table)
        order_clause = " ORDER BY " + ", ".join(quote_sqlite(col) for col in order) if order else ""
        query = f"SELECT {', '.join(quote_sqlite(col) for col in names)} FROM {quote_sqlite(table)}{order_clause}"
        rows = sqlite_connection.execute(query)
        count, digest = row_hashes(rows, [type_name for _, type_name in columns])
        summary[table] = {"rows": count, "sha256": digest}
    return summary


def migrate(source_dsn: str, target: Path, report_path: Path):
    try:
        import psycopg
    except ImportError as error:
        raise RuntimeError("Install psycopg v3 with: python3 -m pip install 'psycopg[binary]>=3.2,<4'") from error

    if not target.is_file():
        raise RuntimeError(f"SQLite database does not exist: {target}; initialize it with Semaphore v2.19.12 first")
    if report_path.exists():
        raise RuntimeError(f"Report already exists: {report_path}; choose a new report path for this run")
    pg = psycopg.connect(source_dsn)
    sqlite_db = sqlite3.connect(target)
    sqlite_db.row_factory = None
    try:
        pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        pg_schema = load_pg_schema(pg)
        target_schema = load_sqlite_schema(sqlite_db)
        source_tables = set(pg_schema) - MIGRATION_TABLES
        target_tables = set(target_schema) - MIGRATION_TABLES
        if source_tables != target_tables:
            missing = sorted(source_tables - target_tables)
            extra = sorted(target_tables - source_tables)
            raise RuntimeError(f"Table mismatch; missing in SQLite={missing}, extra in SQLite={extra}")
        for table in sorted(source_tables):
            pg_cols = [column for column, _ in pg_schema[table]]
            sqlite_cols = [column for column, _ in target_schema[table]]
            if pg_cols != sqlite_cols:
                raise RuntimeError(f"Column mismatch in {table}; PostgreSQL={pg_cols}, SQLite={sqlite_cols}")
            for (column, pg_type), (_, sqlite_type) in zip(pg_schema[table], target_schema[table]):
                if pg_type.lower() not in SUPPORTED_PG_TYPES:
                    raise RuntimeError(f"Unsupported PostgreSQL type {pg_type!r} in {table}.{column}")
                actual = sqlite_affinity(sqlite_type)
                expected = compatible_sqlite_affinities(pg_type)
                if actual not in expected:
                    raise RuntimeError(f"Type mismatch in {table}.{column}: PostgreSQL {pg_type} requires SQLite affinity {sorted(expected)}, found {sqlite_type or '(empty)'} ({actual})")

        # A fresh SQLite schema can contain the bootstrap administrator created
        # by Semaphore. Remove only application rows, retaining its migration log.
        sqlite_db.execute("PRAGMA foreign_keys=OFF")
        sqlite_db.execute("BEGIN IMMEDIATE")
        for table in sorted(target_tables):
            sqlite_db.execute(f"DELETE FROM {quote_sqlite(table)}")

        copied = {}
        for table in sorted(source_tables):
            copied[table] = copy_table(pg, sqlite_db, table, pg_schema[table])

        sequences = update_sequences(pg, sqlite_db, pg_schema)
        sqlite_db.commit()
        sqlite_db.execute("PRAGMA foreign_keys=ON")

        integrity = sqlite_db.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = sqlite_db.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity_check failed: {integrity}")
        if foreign_keys:
            raise RuntimeError(f"SQLite foreign_key_check failed: {foreign_keys[:10]}")

        verified = verify_sqlite(pg, sqlite_db, pg_schema, target_schema)
        for table in copied:
            if copied[table] != verified[table]:
                raise RuntimeError(f"Post-copy row count/checksum mismatch in {table}: source={copied[table]}, sqlite={verified[table]}")

        report = {
            "postgres_tables": len(source_tables),
            "table_results": copied,
            "sequences": sequences,
            "sqlite_integrity_check": integrity,
            "sqlite_foreign_key_violations": len(foreign_keys),
            "sqlite_path": str(target),
        }
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
    except Exception:
        sqlite_db.rollback()
        raise
    finally:
        sqlite_db.close()
        pg.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", type=Path, required=True, help="Initialized SQLite database.sqlite path")
    parser.add_argument("--report", type=Path, required=True, help="Path to write migration counts and checksums")
    args = parser.parse_args()
    source_dsn = os.environ.get("SEMAPHORE_PG_DSN")
    if not source_dsn:
        parser.error("Set SEMAPHORE_PG_DSN in the environment; do not put credentials on the command line")
    try:
        migrate(source_dsn, args.sqlite, args.report)
    except Exception as error:
        print(f"Migration failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
