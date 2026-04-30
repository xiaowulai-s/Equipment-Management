# -*- coding: utf-8 -*-
"""
数据归档与备份服务
Data Archive & Backup Service
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from core.utils.logger import get_logger

logger = get_logger(__name__)


class DataArchiveService:
    """数据归档与备份服务 - 支持数据库备份、数据归档、恢复"""

    def __init__(self, db_path: str, backup_dir: str = "backups") -> None:
        self._db_path = db_path
        self._backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def create_backup(self, tag: str = "") -> Optional[str]:
        """创建数据库完整备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag_suffix = f"_{tag}" if tag else ""
        backup_name = f"backup_{timestamp}{tag_suffix}.db"
        backup_path = os.path.join(self._backup_dir, backup_name)

        try:
            if not os.path.exists(self._db_path):
                logger.error("数据库文件不存在", db_path=self._db_path)
                return None

            conn = sqlite3.connect(self._db_path)
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            conn.close()

            meta_path = backup_path.replace(".db", ".meta.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "timestamp": timestamp,
                        "tag": tag,
                        "source": self._db_path,
                        "type": "full",
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            logger.info("数据库备份成功", backup_path=backup_path)
            return backup_path
        except Exception as e:
            logger.error("数据库备份失败", error=str(e))
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return None

    def restore_backup(self, backup_path: str) -> bool:
        """从备份恢复数据库"""
        try:
            if not os.path.exists(backup_path):
                logger.error("备份文件不存在", backup_path=backup_path)
                return False

            pre_backup = self.create_backup(tag="pre_restore")
            if pre_backup:
                logger.info("恢复前已创建安全备份", backup_path=pre_backup)

            shutil.copy2(backup_path, self._db_path)
            logger.info("数据库恢复成功", backup_path=backup_path)
            return True
        except Exception as e:
            logger.error("数据库恢复失败", error=str(e))
            return False

    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []
        if not os.path.exists(self._backup_dir):
            return backups

        for fname in sorted(os.listdir(self._backup_dir), reverse=True):
            if not fname.endswith(".db"):
                continue
            fpath = os.path.join(self._backup_dir, fname)
            meta_path = fpath.replace(".db", ".meta.json")

            meta = {}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass

            stat = os.stat(fpath)
            backups.append(
                {
                    "filename": fname,
                    "path": fpath,
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "tag": meta.get("tag", ""),
                    "type": meta.get("type", "full"),
                }
            )

        return backups

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """清理旧备份，保留最近 N 个"""
        backups = self.list_backups()
        if len(backups) <= keep_count:
            return 0

        removed = 0
        for backup in backups[keep_count:]:
            try:
                os.remove(backup["path"])
                meta_path = backup["path"].replace(".db", ".meta.json")
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                removed += 1
            except Exception as e:
                logger.warning("删除旧备份失败", path=backup["path"], error=str(e))

        logger.info("清理旧备份完成", removed=removed)
        return removed

    def archive_old_data(self, days: int = 90, archive_dir: str = "archives") -> Optional[str]:
        """归档旧数据到独立数据库"""
        os.makedirs(archive_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        archive_path = os.path.join(archive_dir, f"archive_before_{timestamp}.db")

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

            src_conn = sqlite3.connect(self._db_path)
            dst_conn = sqlite3.connect(archive_path)

            src_conn.backup(dst_conn)
            dst_conn.close()

            cursor = src_conn.cursor()
            tables_to_archive = [
                ("historical_data", "timestamp"),
                ("alarm_records", "timestamp"),
                ("device_status_history", "timestamp"),
                ("system_logs", "timestamp"),
            ]

            archived_total = 0
            for table, time_col in tables_to_archive:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {time_col} < ?", (cutoff_str,))
                    count = cursor.fetchone()[0]
                    if count > 0:
                        cursor.execute(f"DELETE FROM {table} WHERE {time_col} < ?", (cutoff_str,))
                        archived_total += count
                except Exception:
                    pass

            src_conn.commit()
            src_conn.close()

            logger.info("数据归档完成", archive_path=archive_path, archived_count=archived_total, cutoff_days=days)
            return archive_path
        except Exception as e:
            logger.error("数据归档失败", error=str(e))
            if os.path.exists(archive_path):
                os.remove(archive_path)
            return None
