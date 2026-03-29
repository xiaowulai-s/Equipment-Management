# -*- coding: utf-8 -*-
"""Tests for the database migration utility."""

from __future__ import annotations

import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

import migrate_database


def _create_legacy_database(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            name TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            port INTEGER NOT NULL DEFAULT 502,
            slave_id INTEGER NOT NULL DEFAULT 1,
            product_id TEXT,
            group_name TEXT,
            description TEXT,
            status INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO devices (device_id, name, ip_address, port, slave_id, status)
        VALUES ('legacy-1', 'Legacy Device', '192.168.0.10', 502, 7, 1)
        """
    )
    cursor.execute(
        """
        CREATE TABLE register_maps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id VARCHAR(64) NOT NULL,
            name VARCHAR(128) NOT NULL,
            address INTEGER NOT NULL
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO register_maps (device_id, name, address)
        VALUES ('legacy-1', 'Temperature', 100)
        """
    )
    conn.commit()
    conn.close()


@contextmanager
def _workspace_temp_dir() -> Path:
    temp_root = Path.cwd() / ".pytest_runtime_tmp" / "migrate_database_tests"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_root / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_main_migrates_legacy_schema(monkeypatch) -> None:
    with _workspace_temp_dir() as temp_dir:
        db_path = temp_dir / "equipment_management.db"
        _create_legacy_database(db_path)

        monkeypatch.setattr(migrate_database, "DB_PATH", db_path)

        exit_code = migrate_database.main()

        assert exit_code == 0
        assert db_path.with_name(db_path.name + migrate_database.BACKUP_SUFFIX).exists()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(devices)")
        device_columns = {row[1] for row in cursor.fetchall()}
        assert {"id", "name", "device_type", "protocol_type", "host", "unit_id"}.issubset(device_columns)
        assert "device_id" not in device_columns
        assert "ip_address" not in device_columns
        assert "slave_id" not in device_columns

        cursor.execute(
            """
            SELECT id, name, device_type, protocol_type, host, port, unit_id, status
            FROM devices
            """
        )
        migrated_row = cursor.fetchone()
        assert migrated_row == ("legacy-1", "Legacy Device", "Unknown", "modbus_tcp", "192.168.0.10", 502, 7, 1)

        cursor.execute("PRAGMA table_info(register_maps)")
        register_columns = {row[1] for row in cursor.fetchall()}
        assert {
            "function_code",
            "data_type",
            "read_write",
            "scale",
            "unit",
            "description",
            "enabled",
        }.issubset(register_columns)

        conn.close()


def test_main_is_idempotent_for_current_schema(monkeypatch) -> None:
    with _workspace_temp_dir() as temp_dir:
        db_path = temp_dir / "equipment_management.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        migrate_database.create_devices_table(cursor)
        cursor.execute(
            """
            INSERT INTO devices (
                id, name, device_type, protocol_type, host, port, unit_id, use_simulator,
                status, connection_count, error_count
            )
            VALUES ('current-1', 'Current Device', 'PLC', 'modbus_tcp', '10.0.0.1', 502, 1, 0, 0, 0, 0)
            """
        )
        cursor.execute(
            """
            CREATE TABLE register_maps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id VARCHAR(64) NOT NULL,
                name VARCHAR(128) NOT NULL,
                address INTEGER NOT NULL,
                function_code INTEGER DEFAULT 3,
                data_type VARCHAR(32) DEFAULT 'uint16',
                read_write VARCHAR(8) DEFAULT 'R',
                scale FLOAT DEFAULT 1.0,
                unit VARCHAR(32) DEFAULT '',
                description TEXT,
                enabled BOOLEAN DEFAULT 1
            )
            """
        )
        conn.commit()
        conn.close()

        monkeypatch.setattr(migrate_database, "DB_PATH", db_path)

        first_exit_code = migrate_database.main()
        second_exit_code = migrate_database.main()

        assert first_exit_code == 0
        assert second_exit_code == 0

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM devices")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT id, host, unit_id FROM devices")
        assert cursor.fetchone() == ("current-1", "10.0.0.1", 1)
        conn.close()
