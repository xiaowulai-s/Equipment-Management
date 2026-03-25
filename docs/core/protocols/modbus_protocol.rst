Modbus 协议模块
===============

.. module:: core.protocols.modbus_protocol

.. autoclass:: ModbusProtocol
   :members:
   :undoc-members:
   :show-inheritance:

   方法
   ----

   .. method:: crc16(data: bytes) -> int

      计算 CRC16 校验

      :param data: 数据
      :return: CRC16 校验值

   .. method:: lrc(data: bytes) -> int

      计算 LRC 校验（Modbus ASCII 使用）

      :param data: 数据
      :return: LRC 校验值
