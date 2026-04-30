# -*- coding: utf-8 -*-
"""
设备管理接口定义
Device Management Interface Definitions

定义设备管理系统的抽象接口，实现依赖倒置原则（DIP）。
所有模块间通过这些接口交互，不依赖具体实现。

设计原则：
- 接口隔离原则（ISP）：每个接口小而精
- 依赖倒置原则（DIP）：依赖抽象而非具体
- 单一职责原则（SRP）：每个接口只关注一个维度
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Tuple

from PySide6.QtCore import QObject, Signal


# ══════════════════════════════════════════════
# 设备注册表接口
# ══════════════════════════════════════════════


class IDeviceRegistry(ABC):
    """
    设备注册表接口 - 定义设备CRUD操作契约

    职责边界：
    - 设备的增删改查
    - 设备状态查询
    - 设备查找和过滤
    - 不包含：轮询、持久化、连接管理
    """

    @abstractmethod
    def add_device(self, device_config: Dict) -> str:
        """添加设备，返回device_id"""
        ...

    @abstractmethod
    def remove_device(self, device_id: str) -> bool:
        """移除设备"""
        ...

    @abstractmethod
    def get_device(self, device_id: str) -> Optional[Any]:
        """获取设备对象"""
        ...

    @abstractmethod
    def get_all_devices(self) -> List[Dict]:
        """获取所有设备信息列表"""
        ...

    @abstractmethod
    def get_connected_devices(self) -> List[Any]:
        """获取所有已连接的设备对象"""
        ...

    @abstractmethod
    def edit_device(self, device_id: str, new_config: Dict) -> bool:
        """编辑设备配置"""
        ...

    @abstractmethod
    def device_exists(self, device_id: str) -> bool:
        """检查设备是否存在"""
        ...

    @abstractmethod
    def get_device_count(self) -> int:
        """获取设备总数"""
        ...


# ══════════════════════════════════════════════
# 轮询调度器接口
# ══════════════════════════════════════════════


class IPollingScheduler(ABC):
    """
    轮询调度器接口 - 定义异步轮询调度契约

    职责边界：
    - 轮询任务的提交和管理
    - 轮询间隔控制
    - 性能监控统计
    - 不包含：设备CRUD、数据持久化、UI更新
    """

    @abstractmethod
    def start(self) -> None:
        """启动轮询调度器"""
        ...

    @abstractmethod
    def stop(self) -> None:
        """停止轮询调度器"""
        ...

    @abstractmethod
    def set_interval(self, interval_ms: int) -> None:
        """设置轮询间隔"""
        ...

    @abstractmethod
    def get_statistics(self) -> Dict:
        """获取轮询统计信息"""
        ...

    @abstractmethod
    def force_poll(self, device_id: str) -> bool:
        """强制立即轮询指定设备"""
        ...


# ══════════════════════════════════════════════
# 故障恢复服务接口
# ══════════════════════════════════════════════


class IFaultRecoveryService(ABC):
    """
    故障恢复服务接口 - 定义故障处理契约

    职责边界：
    - 故障检测和诊断
    - 自动重连策略
    - 指数退避算法
    - 恢复状态查询
    - 不包含：设备CRUD、轮询调度、数据存储
    """

    @abstractmethod
    def enable_fault_detection(self, device_id: str, enabled: bool) -> bool:
        """启用/禁用故障检测"""
        ...

    @abstractmethod
    def enable_auto_recovery(self, device_id: str, enabled: bool) -> bool:
        """启用/禁用自动恢复"""
        ...

    @abstractmethod
    def set_recovery_mode(self, device_id: str, mode: str) -> bool:
        """设置恢复模式 (auto/manual)"""
        ...

    @abstractmethod
    def set_max_recovery_attempts(self, device_id: str, max_attempts: int) -> bool:
        """设置最大恢复尝试次数"""
        ...

    @abstractmethod
    def get_fault_recovery_status(self, device_id: str) -> Dict:
        """获取故障恢复状态"""
        ...

    @abstractmethod
    def manual_recovery(self, device_id: str) -> bool:
        """手动触发恢复"""
        ...

    @abstractmethod
    def reset_fault(self, device_id: str) -> bool:
        """重置故障状态"""
        ...


# ══════════════════════════════════════════════
# 配置服务接口
# ══════════════════════════════════════════════


class IConfigurationService(ABC):
    """
    配置服务接口 - 定义配置管理契约

    职责边界：
    - 配置导入导出
    - 配置验证
    - 配置持久化
    - 默认配置管理
    - 不包含：设备运行时状态、轮询逻辑
    """

    @abstractmethod
    def export_config(self, file_path: str, device_ids: Optional[List[str]] = None) -> bool:
        """导出设备配置到文件"""
        ...

    @abstractmethod
    def import_config(self, file_path: str, overwrite: bool = False) -> Tuple[bool, int]:
        """从文件导入配置，返回(成功与否, 导入数量)"""
        ...

    @abstractmethod
    def validate_config(self, config: Dict) -> Tuple[bool, str]:
        """验证配置有效性"""
        ...


# ══════════════════════════════════════════════
# 分组管理接口
# ══════════════════════════════════════════════


class IGroupManager(ABC):
    """
    分组管理接口 - 定义设备分组契约

    职责边界：
    - 设备分组管理
    - 轮询组管理
    - 分组查询
    """

    @abstractmethod
    def add_group(self, name: str, **kwargs) -> bool:
        """添加分组"""
        ...

    @abstractmethod
    def remove_group(self, name: str) -> bool:
        """移除分组"""
        ...

    @abstractmethod
    def assign_device(self, device_id: str, group_name: str) -> bool:
        """将设备分配到分组"""
        ...

    @abstractmethod
    def get_group_devices(self, group_name: str) -> List[str]:
        """获取分组中的设备列表"""
        ...

    @abstractmethod
    def get_all_groups(self) -> List[Dict]:
        """获取所有分组信息"""
        ...

    @abstractmethod
    def enable_group(self, group_name: str, enabled: bool) -> bool:
        """启用/禁用分组"""
        ...


# ══════════════════════════════════════════════
# 生命周期管理接口
# ══════════════════════════════════════════════


class ILifecycleManager(ABC):
    """
    生命周期管理接口 - 定义设备连接生命周期契约

    职责边界：
    - 连接/断开管理
    - 重连调度
    - 手动断开跟踪
    """

    @abstractmethod
    def connect_device(self, device_id: str) -> Tuple[bool, str, str]:
        """连接设备，返回(成功, 错误类型, 错误消息)"""
        ...

    @abstractmethod
    def disconnect_device(self, device_id: str) -> None:
        """断开设备连接"""
        ...

    @abstractmethod
    def start(self) -> None:
        """启动生命周期管理器"""
        ...

    @abstractmethod
    def stop(self) -> None:
        """停止生命周期管理器"""
        ...
