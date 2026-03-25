设备管理器模块
================

.. module:: core.device.device_manager

.. autoclass:: DeviceManager
   :members:
   :undoc-members:
   :show-inheritance:

   信号
   ----

   .. signal:: device_added(device_id: str)

      设备添加信号

      :param device_id: 设备 ID

   .. signal:: device_removed(device_id: str)

      设备移除信号

      :param device_id: 设备 ID

   .. signal:: device_connected(device_id: str)

      设备连接信号

   .. signal:: device_disconnected(device_id: str)

      设备断开信号

   .. signal:: device_data_updated(device_id: str, data: dict)

      设备数据更新信号

      :param device_id: 设备 ID
      :param data: 更新的数据

   .. signal:: device_error(device_id: str, error: str)

      设备错误信号

      :param device_id: 设备 ID
      :param error: 错误信息
