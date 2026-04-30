# -*- coding: utf-8 -*-
"""
操作审计日志服务
Audit Log Service - 记录谁在什么时候做了什么操作
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.utils.logger import get_logger

logger = get_logger(__name__)


class AuditLogService:
    """操作审计日志服务 - 记录所有关键操作"""

    def __init__(self, db_manager=None, log_dir: str = "audit_logs") -> None:
        self._db_manager = db_manager
        self._log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._buffer: List[Dict[str, Any]] = []
        self._flush_threshold = 100

    def log_action(
        self,
        action: str,
        target_type: str = "",
        target_id: str = "",
        operator: str = "system",
        details: Optional[Dict[str, Any]] = None,
        result: str = "success",
    ) -> None:
        """记录操作审计日志"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "operator": operator,
            "details": details or {},
            "result": result,
        }

        self._buffer.append(entry)
        logger.info(
            "审计日志: %s %s/%s by %s - %s",
            action,
            target_type,
            target_id,
            operator,
            result,
        )

        if len(self._buffer) >= self._flush_threshold:
            self.flush()

    def flush(self) -> None:
        """将缓冲区写入磁盘"""
        if not self._buffer:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        filepath = os.path.join(self._log_dir, f"audit_{today}.jsonl")

        try:
            with open(filepath, "a", encoding="utf-8") as f:
                for entry in self._buffer:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            self._buffer.clear()
        except Exception as e:
            logger.error("审计日志写入失败", error=str(e))

    def query_logs(
        self,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        operator: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询审计日志"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        filepath = os.path.join(self._log_dir, f"audit_{date}.jsonl")
        if not os.path.exists(filepath):
            return []

        results = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    if action and entry.get("action") != action:
                        continue
                    if target_type and entry.get("target_type") != target_type:
                        continue
                    if target_id and entry.get("target_id") != target_id:
                        continue
                    if operator and entry.get("operator") != operator:
                        continue

                    results.append(entry)
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.error("查询审计日志失败", error=str(e))

        return results

    def get_available_dates(self) -> List[str]:
        """获取有审计日志的日期列表"""
        dates = []
        if not os.path.exists(self._log_dir):
            return dates

        for fname in sorted(os.listdir(self._log_dir), reverse=True):
            if fname.startswith("audit_") and fname.endswith(".jsonl"):
                date_str = fname[6:16]
                dates.append(date_str)

        return dates
