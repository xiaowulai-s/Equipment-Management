# -*- coding: utf-8 -*-
"""
数据导出模块
Data Export Module
"""

import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class DataExporter:
    """数据导出器"""

    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]],
                     file_path: str,
                     include_headers: bool = True,
                     encoding: str = 'utf-8-sig') -> bool:
        """
        导出数据到 CSV 文件
        Args:
            data: 数据列表，每个元素是字典
            file_path: 文件路径
            include_headers: 是否包含表头
            encoding: 文件编码
        Returns:
            bool: 是否成功导出
        """
        try:
            if not data:
                return False

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            fieldnames = list(data[0].keys())

            with open(path, 'w', newline='', encoding=encoding) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if include_headers:
                    writer.writeheader()

                writer.writerows(data)

            return True

        except Exception as e:
            print(f"导出 CSV 失败：{e}")
            return False

    @staticmethod
    def export_device_data_to_csv(devices_data: List[Dict[str, Any]],
                                  file_path: str,
                                  include_headers: bool = True) -> bool:
        """
        导出设备数据到 CSV
        Args:
            devices_data: 设备数据列表
            file_path: 文件路径
            include_headers: 是否包含表头
        Returns:
            bool: 是否成功导出
        """
        try:
            if not devices_data:
                return False

            # 准备导出数据
            export_data = []
            for device in devices_data:
                row = {
                    "设备 ID": device.get("device_id", ""),
                    "设备名称": device.get("name", ""),
                    "设备类型": device.get("type", ""),
                    "状态": device.get("status_text", ""),
                    "IP 地址": device.get("ip_address", ""),
                    "端口": device.get("port", ""),
                }

                # 添加当前数据
                current_data = device.get("current_data", {})
                for param_name, param_info in current_data.items():
                    row[f"{param_name}({param_info.get('unit', '')})"] = param_info.get("value", "")

                row["导出时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                export_data.append(row)

            return DataExporter.export_to_csv(export_data, file_path, include_headers)

        except Exception as e:
            print(f"导出设备数据失败：{e}")
            return False

    @staticmethod
    def export_alarm_history_to_csv(alarms: List[Dict[str, Any]],
                                    file_path: str,
                                    include_headers: bool = True) -> bool:
        """
        导出报警历史到 CSV
        Args:
            alarms: 报警列表
            file_path: 文件路径
            include_headers: 是否包含表头
        Returns:
            bool: 是否成功导出
        """
        try:
            if not alarms:
                return False

            export_data = []
            for alarm in alarms:
                row = {
                    "报警 ID": alarm.get("alarm_id", ""),
                    "设备 ID": alarm.get("device_id", ""),
                    "参数": alarm.get("parameter", ""),
                    "报警类型": alarm.get("alarm_type", ""),
                    "级别": alarm.get("level_name", ""),
                    "值": alarm.get("value", ""),
                    "阈值 (高)": alarm.get("threshold_high", ""),
                    "阈值 (低)": alarm.get("threshold_low", ""),
                    "描述": alarm.get("description", ""),
                    "时间": alarm.get("timestamp", ""),
                    "已确认": "是" if alarm.get("acknowledged") else "否",
                    "已清除": "是" if alarm.get("cleared") else "否"
                }
                export_data.append(row)

            return DataExporter.export_to_csv(export_data, file_path, include_headers)

        except Exception as e:
            print(f"导出报警历史失败：{e}")
            return False

    @staticmethod
    def export_to_json(data: Any, file_path: str, indent: int = 2) -> bool:
        """
        导出数据到 JSON 文件
        Args:
            data: 数据
            file_path: 文件路径
            indent: 缩进空格数
        Returns:
            bool: 是否成功导出
        """
        try:
            import json

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent, default=str)

            return True

        except Exception as e:
            print(f"导出 JSON 失败：{e}")
            return False

    @staticmethod
    def export_to_excel(data: List[Dict[str, Any]],
                       file_path: str,
                       sheet_name: str = "数据",
                       include_headers: bool = True) -> bool:
        """
        导出数据到 Excel 文件
        Args:
            data: 数据列表
            file_path: 文件路径
            sheet_name: 工作表名称
            include_headers: 是否包含表头
        Returns:
            bool: 是否成功导出
        """
        try:
            from openpyxl import Workbook

            if not data:
                return False

            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            wb = Workbook()
            ws = wb.active
            ws.title = sheet_name

            # 写入表头
            if include_headers:
                headers = list(data[0].keys())
                for col, header in enumerate(headers, 1):
                    ws.cell(row=1, column=col, value=header)

                # 设置表头样式
                from openpyxl.styles import Font, PatternFill
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

                for col in range(1, len(headers) + 1):
                    cell = ws.cell(row=1, column=col)
                    cell.font = header_font
                    cell.fill = header_fill

            # 写入数据
            for row_idx, row_data in enumerate(data, 2 if include_headers else 1):
                for col_idx, value in enumerate(row_data.values(), 1):
                    ws.cell(row=row_idx, column=col_idx, value=value)

            # 自动调整列宽
            for column in ws.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                if adjusted_width > 50:
                    adjusted_width = 50
                ws.column_dimensions[column[0].column_letter].width = adjusted_width

            wb.save(path)
            return True

        except ImportError:
            print("错误：需要安装 openpyxl 库 (pip install openpyxl)")
            return False
        except Exception as e:
            print(f"导出 Excel 失败：{e}")
            return False

    @staticmethod
    def generate_export_filename(prefix: str = "export",
                                extension: str = "csv") -> str:
        """
        生成导出文件名
        Args:
            prefix: 文件名前缀
            extension: 文件扩展名
        Returns:
            str: 文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
