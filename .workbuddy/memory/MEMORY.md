# 工业设备管理系统 - 项目记忆

## 当前版本: v1.5.2 (2026-03-29)

## 架构
- **四层解耦**: 协议层(src/protocols/) → 通信层(src/communication/) → 设备层(src/device/) → 数据/UI层(src/data/ + ui/)
- **UI框架**: PySide6 Widgets (非QML), 主窗口 ui/main_window_v2.py
- **主窗口**: ui/main_window_v2.py (基于core/旧架构DeviceManagerV2)

## 技术栈
- Python 3.14.2, PySide6 6.10.2, SQLAlchemy 2.0, pyqtgraph, pytest 9.0.2
- QThread + 信号槽 (严禁UI线程I/O)

## 项目结构
- `src/` - 新架构核心源码 (协议/通信/设备/数据/报警)
- `core/` - 旧架构核心 (DeviceManagerV2, 实际UI仍依赖此)
- `ui/` - UI层 (main_window_v2.py, dialogs/, widgets/, styles/)
- `config/` - 配置 (default_config.json, pump_station_a.json)
- `tests/` - 测试 (pytest, 1800+项)
- `docs/` - 文档 (project/architecture/ai/design/reports/meta 子目录)
- `scripts/` - 工具脚本 (build.py, main_v2.py, migrate_database.py等)
- `assets/` - 资源文件 (截图)

## 主题系统 (已简化)
- 仅浅色主题, ThemeManager在ui/theme_manager.py
- QSS文件: base.qss, base_light.qss, light.qss
- 已删除: 深色主题支持, theme_toggle_button.py, theme_preference.py

## 关键设计
- **设备默认配置**: 5个Modbus TCP + 5个Modbus RTU (use_simulator=True)
- **手动断开**: _manually_disconnected set 防止自动重连
- **状态栏**: 显示 总设备/在线/离线/错误 数量
- **按钮**: PrimaryButton(蓝/编辑), SuccessButton(绿/连接), DangerButton(红/断开)
- **数据持久化**: DatabaseManager + 6表ORM + 5个Repository
- **报警**: AlarmManager(信号聚合+持久化), Register._check_alarm(阈值检测)
- **报警规则配置**: ui/alarm_config_dialog.py (AlarmConfigDialog + _AddRuleDialog), 运行时内存模式
- **循环导入**: core.utils.alarm_manager ↔ core.data.alarm_rule_persistence 存在已知循环导入
- **枚举注意**: DataType/ProtocolType的.value可能是tuple, 取[0]作字符串存储

## 版本号位置
- pyproject.toml, src/__init__.py, core/version.py, config.json, config/default_config.json, README.md, CHANGELOG.md

## GitHub
- 仓库: https://github.com/xiaowulai-s/Equipment-Management
