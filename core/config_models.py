# -*- coding: utf-8 -*-
"""
配置模型定义
Configuration Models using Pydantic
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterMapConfig(BaseModel):
    """寄存器映射配置"""

    model_config = ConfigDict(validate_assignment=True)

    name: str = Field(..., description="变量名称")
    address: int = Field(..., ge=0, le=65535, description="寄存器地址")
    function_code: int = Field(default=3, ge=1, le=255, description="功能码")
    data_type: Literal["uint16", "int16", "uint32", "int32", "float32", "float64", "bool"] = Field(
        default="uint16", description="数据类型"
    )
    read_write: Literal["R", "W", "RW"] = Field(default="R", description="读写权限")
    scale: float = Field(default=1.0, description="缩放因子")
    unit: str = Field(default="", description="单位")
    description: str = Field(default="", description="描述")
    enabled: bool = Field(default=True, description="是否启用")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("变量名称不能为空")
        return v.strip()


class DeviceConfig(BaseModel):
    """设备配置"""

    model_config = ConfigDict(validate_assignment=True)

    device_id: Optional[str] = Field(default=None, description="设备ID")
    name: str = Field(..., min_length=1, max_length=128, description="设备名称")
    device_type: str = Field(default="通用设备", description="设备类型")
    device_number: Optional[str] = Field(default=None, description="设备编号")
    protocol_type: Literal["modbus_tcp", "modbus_rtu"] = Field(default="modbus_tcp", description="协议类型")

    # Modbus TCP 参数
    host: Optional[str] = Field(default="127.0.0.1", description="主机地址")
    port: int = Field(default=502, ge=1, le=65535, description="端口号")
    unit_id: int = Field(default=1, ge=0, le=255, description="从站地址")

    # Modbus RTU 参数
    serial_port: Optional[str] = Field(default=None, description="串口号")
    baudrate: int = Field(default=9600, description="波特率")
    bytesize: int = Field(default=8, ge=5, le=8, description="数据位")
    parity: Literal["N", "E", "O", "M", "S"] = Field(default="N", description="校验位")
    stopbits: int = Field(default=1, ge=1, le=2, description="停止位")

    # 模拟器
    use_simulator: bool = Field(default=False, description="使用模拟器")

    # 寄存器映射
    register_map: List[RegisterMapConfig] = Field(default_factory=list, description="寄存器映射列表")

    # 采集配置
    poll_interval: int = Field(default=1000, ge=100, le=60000, description="采集间隔(ms)")
    timeout: int = Field(default=5000, ge=1000, le=30000, description="超时时间(ms)")
    retry_count: int = Field(default=3, ge=0, le=10, description="重试次数")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("设备名称不能为空")
        return v.strip()

    def to_db_dict(self) -> Dict[str, Any]:
        """转换为数据库模型字典"""
        return {
            "id": self.device_id,
            "name": self.name,
            "device_type": self.device_type,
            "device_number": self.device_number,
            "protocol_type": self.protocol_type,
            "host": self.host if self.protocol_type == "modbus_tcp" else None,
            "port": self.port if self.protocol_type == "modbus_tcp" else None,
            "unit_id": self.unit_id,
            "use_simulator": self.use_simulator,
        }

    @classmethod
    def from_db_dict(cls, data: Dict[str, Any], register_maps: List[Dict] = None) -> "DeviceConfig":
        """从数据库模型创建配置"""
        config_data = {
            "device_id": data.get("id"),
            "name": data.get("name"),
            "device_type": data.get("device_type"),
            "device_number": data.get("device_number"),
            "protocol_type": data.get("protocol_type"),
            "host": data.get("host"),
            "port": data.get("port"),
            "unit_id": data.get("unit_id", 1),
            "use_simulator": data.get("use_simulator", False),
            "register_map": [RegisterMapConfig(**r) for r in (register_maps or [])],
        }
        return cls(**config_data)


class AlarmRuleConfig(BaseModel):
    """报警规则配置"""

    model_config = ConfigDict(validate_assignment=True)

    rule_id: str = Field(..., description="规则ID")
    device_id: str = Field(default="*", description="设备ID，*表示所有设备")
    parameter: str = Field(..., description="参数名称")
    alarm_type: Literal["threshold_high", "threshold_low", "threshold_range", "rate_of_change", "communication"] = (
        Field(..., description="报警类型")
    )
    threshold_high: Optional[float] = Field(default=None, description="高阈值")
    threshold_low: Optional[float] = Field(default=None, description="低阈值")
    rate_limit: Optional[float] = Field(default=None, description="变化率限制")
    level: Literal[0, 1, 2] = Field(default=1, description="报警级别: 0=信息, 1=警告, 2=严重")
    enabled: bool = Field(default=True, description="是否启用")
    description: str = Field(default="", description="描述")

    @field_validator("rule_id")
    @classmethod
    def validate_rule_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("规则ID不能为空")
        return v.strip()


class ApplicationConfig(BaseModel):
    """应用程序配置"""

    model_config = ConfigDict(validate_assignment=True)

    # 数据库配置
    database_path: str = Field(default="data/equipment_management.db", description="数据库路径")

    # 日志配置
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="日志级别")
    log_file: str = Field(default="logs/app.log", description="日志文件路径")
    max_log_size: int = Field(default=10 * 1024 * 1024, description="单个日志文件最大大小(字节)")
    log_backup_count: int = Field(default=5, description="日志备份数量")

    # UI配置
    theme: Literal["light", "dark", "auto"] = Field(default="light", description="主题")
    language: str = Field(default="zh_CN", description="语言")
    window_width: int = Field(default=1600, ge=800, description="窗口宽度")
    window_height: int = Field(default=900, ge=600, description="窗口高度")

    # 数据保留配置
    history_retention_days: int = Field(default=30, ge=1, le=365, description="历史数据保留天数")
    alarm_retention_days: int = Field(default=90, ge=1, le=365, description="报警记录保留天数")
    log_retention_days: int = Field(default=7, ge=1, le=30, description="日志保留天数")

    # 性能配置
    max_devices: int = Field(default=100, ge=1, le=1000, description="最大设备数量")
    max_poll_rate: int = Field(default=100, ge=10, description="最大采集频率(ms)")
    connection_pool_size: int = Field(default=10, ge=1, le=100, description="连接池大小")


class SystemConfig(BaseModel):
    """系统完整配置"""

    model_config = ConfigDict(validate_assignment=True)

    version: str = Field(default="2.0.0", description="配置版本")
    application: ApplicationConfig = Field(default_factory=ApplicationConfig, description="应用配置")
    devices: List[DeviceConfig] = Field(default_factory=list, description="设备配置列表")
    alarm_rules: List[AlarmRuleConfig] = Field(default_factory=list, description="报警规则列表")
