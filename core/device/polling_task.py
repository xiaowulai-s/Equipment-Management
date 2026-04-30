# -*- coding: utf-8 -*-
"""
设备轮询任务 - QRunnable实现
Device Polling Task for Thread Pool Execution

将阻塞式Modbus通信从主线程移至工作线程池，
彻底解决UI冻结问题。
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QRunnable, Signal

try:
    from ui.async_utils import async_wait
    ASYNC_UTILS_AVAILABLE = True
except ImportError:
    ASYNC_UTILS_AVAILABLE = False


class DevicePollingTask(QRunnable):
    """
    设备轮询任务 - 提交到QThreadPool执行
    
    特点：
    - 每个设备独立一个Task实例
    - 自动删除（setAutoDelete(True)）
    - 通过Signal跨线程传递结果
    - 完善的异常处理和超时管理
    """
    
    class Signals(QObject):
        """信号定义（QObject子类才能定义Signal）"""
        
        # ✅ 成功完成轮询
        poll_success = Signal(str, dict, float)  # device_id, data, response_time_ms
        
        # ⚠️ 轮询失败
        poll_failed = Signal(str, str, str)      # device_id, error_type, error_msg
        
        # ⏰ 轮询超时
        poll_timeout = Signal(str, float)         # device_id, elapsed_ms
        
        # 📊 性能监控
        performance_warning = Signal(str, str)    # device_id, warning_message
    
    def __init__(
        self,
        device_id: str,
        device_obj: Any,
        protocol: Any,
        persistence_svc: Any,
        fault_recovery_mgr: Any,
    ):
        super().__init__()
        
        self.setAutoDelete(True)  # 执行完后自动释放内存
        
        self._device_id = device_id
        self._device = device_obj
        self._protocol = protocol
        self._persistence_svc = persistence_svc
        self._fault_recovery_mgr = fault_recovery_mgr
        
        # 信号对象（必须在主线程创建）
        self.signals = self.Signals()
    
    def run(self) -> None:
        """
        在线程池的工作线程中执行设备轮询
        
        此方法完全在工作线程中运行，不阻塞UI线程！
        包含完整的错误处理和性能监控。
        """
        start_time = time.monotonic()
        
        try:
            # 1️⃣ 检查设备状态
            if not hasattr(self._device, 'get_status'):
                self.signals.poll_failed.emit(
                    self._device_id,
                    "invalid_device",
                    "设备对象缺少get_status方法"
                )
                return
            
            from core.device.device_model import DeviceStatus
            if self._device.get_status() != DeviceStatus.CONNECTED:
                return  # 设备未连接，跳过
            
            # 2️⃣ 执行实际的数据轮询（可能阻塞15-25ms）
            data = self._device.poll_data()
            
            elapsed_ms = (time.monotonic() - start_time) * 1000
            
            # 3️⃣ 处理轮询结果
            if data and isinstance(data, dict):
                
                # 持久化存储: 仅在 DataBus 未订阅时直接调用
                # 如果 DataBus 已订阅，数据会通过 DataBus → _on_data_updated → persist_data 自动持久化
                # 避免双重写入
                try:
                    if self._persistence_svc is not None and not self._persistence_svc.is_subscribed:
                        self._persistence_svc.persist_data(self._device_id, data)
                except Exception as persist_err:
                    pass
                
                # 发送成功信号（跨线程安全）
                self.signals.poll_success.emit(
                    self._device_id,
                    data,
                    elapsed_ms
                )
                
                # 4️⃣ 性能监控：如果响应时间过长，发出警告
                if elapsed_ms > 100:  # >100ms 认为异常慢
                    self.signals.performance_warning.emit(
                        self._device_id,
                        f"轮询响应时间过长: {elapsed_ms:.1f}ms (正常<50ms)"
                    )
                
            else:
                # ❌ 无数据返回（超时或协议错误）
                self.signals.poll_timeout.emit(
                    self._device_id,
                    elapsed_ms
                )
        
        except ConnectionError as conn_err:
            # 网络连接断开
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self.signals.poll_failed.emit(
                self._device_id,
                "connection_error",
                f"连接错误: {str(conn_err)}"
            )
        
        except TimeoutError as timeout_err:
            # Modbus超时
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self.signals.poll_timeout.emit(
                self._device_id,
                elapsed_ms
            )
        
        except Exception as e:
            # 其他未知错误
            elapsed_ms = (time.monotonic() - start_time) * 1000
            error_type = type(e).__name__
            error_msg = str(e)
            
            self.signals.poll_failed.emit(
                self._device_id,
                error_type.lower(),
                error_msg
            )
            
            # 详细日志记录（便于调试）
            import traceback
            traceback.print_exc()
