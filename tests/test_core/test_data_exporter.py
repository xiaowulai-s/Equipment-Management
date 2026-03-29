# -*- coding: utf-8 -*-
"""Tests for data export helpers."""

from __future__ import annotations

import json
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path

from core.utils.data_exporter import DataExporter


@contextmanager
def _workspace_temp_dir() -> Path:
    temp_root = Path.cwd() / ".pytest_runtime_tmp" / "data_exporter_tests"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_root / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_export_device_data_to_csv_supports_normalized_fields() -> None:
    with _workspace_temp_dir() as temp_dir:
        output = temp_dir / "devices.csv"
        success = DataExporter.export_device_data_to_csv(
            [
                {
                    "device_id": "dev-1",
                    "name": "Pump A",
                    "device_type": "Pump",
                    "status_text": "Connected",
                    "host": "192.168.1.10",
                    "port": 502,
                    "unit_id": 3,
                    "current_data": {
                        "pressure": {"value": 12.5, "unit": "bar"},
                        "running": True,
                    },
                }
            ],
            str(output),
        )

        assert success is True
        content = output.read_text(encoding="utf-8-sig")
        assert "设备 ID" in content
        assert "主机地址" in content
        assert "pressure(bar)" in content
        assert "Pump A" in content


def test_export_alarm_history_to_csv_uses_fallback_alarm_id() -> None:
    with _workspace_temp_dir() as temp_dir:
        output = temp_dir / "alarms.csv"
        success = DataExporter.export_alarm_history_to_csv(
            [
                {
                    "id": 7,
                    "device_id": "dev-1",
                    "parameter": "temperature",
                    "alarm_type": "threshold_high",
                    "level_name": "严重",
                    "value": 88.2,
                    "threshold_high": 80,
                    "acknowledged": True,
                    "cleared": False,
                }
            ],
            str(output),
        )

        assert success is True
        content = output.read_text(encoding="utf-8-sig")
        assert "报警 ID" in content
        assert "严重" in content
        assert "是" in content
        assert "否" in content


def test_export_to_json_and_filename_generation() -> None:
    with _workspace_temp_dir() as temp_dir:
        output = temp_dir / "payload.json"
        payload = {"device_id": "dev-1", "value": 42}

        assert DataExporter.export_to_json(payload, str(output)) is True
        assert json.loads(output.read_text(encoding="utf-8")) == payload

        filename = DataExporter.generate_export_filename(prefix="report", extension="json")
        assert filename.startswith("report_")
        assert filename.endswith(".json")
