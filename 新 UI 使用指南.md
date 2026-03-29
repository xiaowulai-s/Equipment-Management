# 新 UI 快速使用指南

## 🚀 5 分钟快速上手

### 1. 查看演示效果

```bash
python test_new_ui.py
```

您将看到：
- 📊 6 个数据卡片（温度、压力、流量等）
- 🏷️ 5 个状态徽章（在线/离线/连接中/错误/警告）
- 🔔 4 个报警横幅（不同级别）
- ⚡ 6 个快捷操作卡片

---

### 2. 使用新样式

#### 深色主题
```python
from ui.modern_styles import ModernStyles

# 应用到主窗口
self.setStyleSheet(
    ModernStyles.MAIN_WINDOW_DARK +
    ModernStyles.CENTRAL_WIDGET_DARK
)
```

#### 浅色主题
```python
self.setStyleSheet(
    ModernStyles.MAIN_WINDOW_LIGHT +
    ModernStyles.CENTRAL_WIDGET_LIGHT
)
```

---

### 3. 使用数据卡片

```python
from ui.data_cards import DataCard

# 创建卡片
card = DataCard(
    name="温度",
    value="75.5",
    unit="°C",
    is_dark=True  # 深色主题
)

# 更新数值和状态
card.update_value("80.2", status="warning")

# 响应点击
card.clicked.connect(lambda: print("卡片被点击"))

# 添加到布局
layout.addWidget(card)
```

---

### 4. 使用状态徽章

```python
from ui.data_cards import StatusBadge

# 创建徽章
badge = StatusBadge(status="online", is_dark=True)

# 更新状态
badge.set_status("error")  # 显示红色"错误"
```

**支持的状态**:
- `"online"` - 已连接（绿色）
- `"offline"` - 未连接（灰色）
- `"connecting"` - 连接中（蓝色）
- `"error"` - 错误（红色）
- `"warning"` - 警告（黄色）

---

### 5. 使用报警横幅

```python
from ui.data_cards import AlarmBanner

# 创建报警
alarm = AlarmBanner(
    level="warning",      # info/warning/error/critical
    message="温度过高",
    device_id="PUMP-001",
    is_dark=True
)

# 响应确认
alarm.acknowledged.connect(on_acknowledge)

# 添加到布局
layout.addWidget(alarm)
```

**报警级别**:
- `"info"` - 信息（蓝色）
- `"warning"` - 警告（黄色）
- `"error"` - 错误（红色）
- `"critical"` - 严重（深红色）

---

### 6. 使用快捷操作卡片

```python
from ui.data_cards import QuickActionCard

# 创建卡片
card = QuickActionCard(
    icon="📊",
    title="数据导出",
    is_dark=True
)

# 响应点击
card.clicked.connect(export_data)

# 添加到布局
layout.addWidget(card)
```

---

## 📋 完整示例

```python
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from ui.data_cards import DataCard, StatusBadge, AlarmBanner
from ui.modern_styles import ModernStyles

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 应用深色主题
        self.setStyleSheet(ModernStyles.MAIN_WINDOW_DARK)

        # 中央组件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 添加数据卡片
        temp_card = DataCard("温度", "75.5", "°C", is_dark=True)
        layout.addWidget(temp_card)

        # 添加状态徽章
        status_badge = StatusBadge("online", is_dark=True)
        layout.addWidget(status_badge)

        # 添加报警横幅
        alarm = AlarmBanner("warning", "温度偏高", "PUMP-001", is_dark=True)
        layout.addWidget(alarm)
```

---

## 🎨 样式定制

### 修改颜色
```python
from ui.modern_styles import ThemeColor

# 使用预定义颜色
primary_blue = ThemeColor.PRIMARY_BLUE.value  # "#0969DA"
success_green = ThemeColor.SUCCESS_GREEN.value  # "#1A7F37"
```

### 自定义组件样式
```python
card = DataCard("自定义", "100", "%", is_dark=True)
card.setStyleSheet("""
    DataCard {
        background-color: #161B22;
        border: 2px solid #58A6FF;
        border-radius: 12px;
    }
""")
```

---

## 🔧 常见问题

### Q: 如何切换到浅色主题？
A: 将 `is_dark=False` 传递给组件，或使用 `ModernStyles.*_LIGHT` 样式

### Q: 数据卡片的大小可以调整吗？
A: 可以，使用 `setFixedHeight()` 和 `setMinimumWidth()` 方法

### Q: 如何让报警横幅闪烁？
A: 使用 `QPropertyAnimation` 动画（参考原 `styles.py` 中的动画示例）

### Q: 可以混合使用新旧样式吗？
A: 可以，新旧样式完全兼容，但建议统一使用新样式

---

## 📚 更多信息

- 📖 [UI 重构报告](./UI 重构报告.md) - 详细技术文档
- 📖 [完成总结](./UI 重构完成总结.md) - 完整交付清单
- 💻 `test_new_ui.py` - 可运行的演示程序
- 📁 `ui/modern_styles.py` - 样式系统源码
- 📁 `ui/data_cards.py` - 组件源码

---

**最后更新**: 2026-03-26
**版本**: v1.2.0
