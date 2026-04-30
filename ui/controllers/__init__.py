# -*- coding: utf-8 -*-
"""
UI Controllers package.

Controller 层职责:
- 异步调度（QThreadPool + QRunnable）
- Signal 中转（Controller → MainWindow）
- 轮询管理（QTimer）
- DataBus 订阅

不包含:
- 业务逻辑（在 Service 层）
- UI 操作（在 MainWindow）
"""

from .status_bar_controller import StatusBarController
from .monitor_page_controller import MonitorPageController
from .mcgs_controller import MCGSController
from .device_controller import DeviceController
