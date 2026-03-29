# 工业设备管理系统 - Python环境UI设计方案

## 一、设计系统概述

本设计方案基于原始UI设计方案，针对 **PySide6 + Python** 技术栈进行适配。将CSS样式系统转换为Python/QSS样式表，并提供完整的组件实现示例。

**核心设计原则：**
- 🎯 **信息密度适中** - 既不过于拥挤也不过于稀疏，保证关键数据一目了然
- 🔍 **层次分明** - 通过视觉权重引导用户注意力，重要信息优先呈现
- ⚡ **操作高效** - 常用操作路径最短，减少点击次数
- 🌙 **工业级配色** - 深色主题减少视觉疲劳，适合长时间监控
- ♿ **无障碍友好** - 符合WCAG AA标准，色对比度≥4.5:1

---

## 二、设计系统基础

### 2.1 色彩系统 (Python定义)

#### 2.1.1 主色调 (Primary Colors)

```python
# 品牌主色 - 科技蓝
COLOR_PRIMARY_50 = "#E3F2FD"   # 浅蓝背景
COLOR_PRIMARY_100 = "#BBDEFB"   # 悬停背景
COLOR_PRIMARY_200 = "#90CAF9"   # 次要强调
COLOR_PRIMARY_300 = "#64B5F6"   # 边框
COLOR_PRIMARY_400 = "#42A5F5"   # 图标
COLOR_PRIMARY_500 = "#2196F3"   # 主色 (基准)
COLOR_PRIMARY_600 = "#1E88E5"   # 主色-深
COLOR_PRIMARY_700 = "#1976D2"   # 主色-更深
COLOR_PRIMARY_800 = "#1565C0"   # 主色-最深
COLOR_PRIMARY_900 = "#0D47A1"   # 标题强调

# 辅助色 - 青色 (数据可视化)
COLOR_ACCENT_400 = "#26C6DA"
COLOR_ACCENT_500 = "#00BCD4"
COLOR_ACCENT_600 = "#00ACC1"
```

#### 2.1.2 功能色 (Semantic Colors)

```python
# 成功状态 - 运行正常
COLOR_SUCCESS_50 = "#E8F5E9"
COLOR_SUCCESS_100 = "#C8E6C9"
COLOR_SUCCESS_400 = "#66BB6A"
COLOR_SUCCESS_500 = "#4CAF50"   # 正常-深
COLOR_SUCCESS_600 = "#43A047"

# 警告状态 - 需要注意
COLOR_WARNING_50 = "#FFF8E1"
COLOR_WARNING_100 = "#FFECB3"
COLOR_WARNING_400 = "#FFCA28"
COLOR_WARNING_500 = "#FFC107"   # 警告-深
COLOR_WARNING_600 = "#FFB300"

# 错误状态 - 故障/离线
COLOR_ERROR_50 = "#FFEBEE"
COLOR_ERROR_100 = "#FFCDD2"
COLOR_ERROR_400 = "#EF5350"
COLOR_ERROR_500 = "#F44336"   # 错误-深
COLOR_ERROR_600 = "#E53935"

# 信息状态 - 提示/中性
COLOR_INFO_50 = "#E3F2FD"
COLOR_INFO_100 = "#BBDEFB"
COLOR_INFO_400 = "#42A5F5"
COLOR_INFO_500 = "#2196F3"   # 信息-深
```

#### 2.1.3 中性色 (Neutral Colors)

```python
# 灰度系统
COLOR_GRAY_25 = "#FCFCFD"    # 最浅背景
COLOR_GRAY_50 = "#F9FAFB"    # 页面背景
COLOR_GRAY_100 = "#F3F4F6"    # 卡片背景
COLOR_GRAY_200 = "#E5E7EB"    # 边框-浅
COLOR_GRAY_300 = "#D1D5DB"    # 边框-中
COLOR_GRAY_400 = "#9CA3AF"    # 占位符
COLOR_GRAY_500 = "#6B7280"    # 辅助文本
COLOR_GRAY_600 = "#4B5563"    # 正文文本
COLOR_GRAY_700 = "#374151"    # 标题文本
COLOR_GRAY_800 = "#1F2937"    # 深色文本
COLOR_GRAY_900 = "#111827"    # 最深文本
```

#### 2.1.4 深色主题背景

```python
# 深色主题色彩定义
DARK_THEME = {
    # 背景色 - 由浅到深
    "bg_base": "#0F1419",       # 最深层
    "bg_raised": "#161B22",     # 卡片/面板
    "bg_overlay": "#1C2128",    # 弹窗/下拉
    "bg_hover": "#21262D",       # 悬停态

    # 深色文本
    "text_primary": "#E6EDF3",   # 主要文本
    "text_secondary": "#8B949E", # 次要文本
    "text_tertiary": "#6E7681",  # 禁用/提示
    "text_inverse": "#0D1117",   # 反色文本

    # 深色边框
    "border_default": "#30363D", # 默认边框
    "border_muted": "#21262D",   # 弱边框
    "border_accent": "#388BFD",  # 强调边框

    # 状态色
    "status_online": "#3FB950",
    "status_offline": "#F85149",
    "status_warning": "#D29922",
}
```

---

### 2.2 字体系统

#### 2.2.1 字体族定义

```python
# 字体配置 - QFont
FONT_SANS = "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
FONT_MONO = "JetBrains Mono, Fira Code, Consolas, monospace"

# 字号配置
FONT_SIZE_DISPLAY = "40px"    # 页面大标题
FONT_SIZE_H1 = "32px"        # 模块标题
FONT_SIZE_H2 = "24px"         # 卡片标题
FONT_SIZE_H3 = "20px"         # 分组标题
FONT_SIZE_H4 = "18px"         # 区块标题
FONT_SIZE_BODY_LG = "16px"    # 主要内容
FONT_SIZE_BODY = "15px"       # 默认正文
FONT_SIZE_BODY_SM = "14px"    # 次要信息
FONT_SIZE_CAPTION = "13px"    # 说明文字
FONT_SIZE_DATA_LG = "32px"    # 仪表盘数值
FONT_SIZE_DATA = "24px"       # 关键数据
```

#### 2.2.2 Python字体设置示例

```python
from PySide6.QtGui import QFont

def get_font(family: str = "Inter", size: int = 14, weight: int = QFont.Weight.Normal) -> QFont:
    """创建统一字体"""
    font = QFont(family, size)
    font.setWeight(weight)
    return font

# 常用字体
def get_title_font():
    return get_font("Inter", 24, QFont.Weight.DemiBold)

def get_body_font():
    return get_font("Inter", 14, QFont.Weight.Normal)

def get_mono_font():
    return get_font("JetBrains Mono", 14, QFont.Weight.Medium)

def get_data_font():
    return get_font("Inter", 32, QFont.Weight.Bold)
```

---

### 2.3 间距系统

#### 2.3.1 基础间距单位 (基于4px网格)

```python
# 间距常量 (单位: px)
SPACE_0 = 0
SPACE_PX = 1
SPACE_0_5 = 2    # 0.125rem = 2px
SPACE_1 = 4      # 0.25rem = 4px
SPACE_1_5 = 6    # 0.375rem = 6px
SPACE_2 = 8      # 0.5rem = 8px
SPACE_2_5 = 10   # 0.625rem = 10px
SPACE_3 = 12     # 0.75rem = 12px
SPACE_3_5 = 14   # 0.875rem = 14px
SPACE_4 = 16     # 1rem = 16px
SPACE_5 = 20     # 1.25rem = 20px
SPACE_6 = 24     # 1.5rem = 24px
SPACE_8 = 32     # 2rem = 32px
SPACE_10 = 40    # 2.5rem = 40px
SPACE_12 = 48    # 3rem = 48px
SPACE_16 = 64    # 4rem = 64px

# 组件间距
PADDING_BUTTON = (SPACE_3, SPACE_4)      # 按钮内边距 (12px, 16px)
PADDING_INPUT = (SPACE_2, SPACE_3)        # 输入框内边距 (8px, 12px)
PADDING_CARD = SPACE_4                    # 卡片内边距 16px
PADDING_SECTION = SPACE_6                 # 区块间距 24px

# 组件间间距
GAP_XS = SPACE_1    # 4px - 紧凑元素
GAP_SM = SPACE_2    # 8px - 关联元素
GAP_MD = SPACE_4    # 16px - 分组元素
GAP_LG = SPACE_6    # 24px - 区块元素
GAP_XL = SPACE_8    # 32px - 页面区域
```

---

### 2.4 圆角系统

```python
# 圆角常量 (单位: px)
RADIUS_NONE = 0
RADIUS_SM = 4      # 0.25rem = 4px - 小元素
RADIUS_MD = 6       # 0.375rem = 6px - 默认
RADIUS_LG = 8        # 0.5rem = 8px - 卡片
RADIUS_XL = 12       # 0.75rem = 12px - 大卡片
RADIUS_2XL = 16      # 1rem = 16px - 特殊
RADIUS_FULL = 9999   # 圆形

# 圆角应用
RADIUS_BUTTON = RADIUS_MD
RADIUS_INPUT = RADIUS_MD
RADIUS_CARD = RADIUS_LG
RADIUS_MODAL = RADIUS_XL
RADIUS_BADGE = RADIUS_SM
```

---

### 2.5 阴影系统

```python
# 阴影定义 (x, y, blur, spread, color)
SHADOW_XS = "0 1px 2px rgba(0, 0, 0, 0.05)"
SHADOW_SM = "0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)"
SHADOW_MD = "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
SHADOW_LG = "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
SHADOW_XL = "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"

# 工业风格阴影 (带蓝调)
SHADOW_INDUSTRIAL_SM = "0 2px 4px rgba(33, 150, 243, 0.08)"
SHADOW_INDUSTRIAL_MD = "0 4px 12px rgba(33, 150, 243, 0.12)"
SHADOW_INDUSTRIAL_LG = "0 8px 24px rgba(33, 150, 243, 0.16)"

# 发光效果 (用于状态指示)
GLOW_SUCCESS = "0 0 12px rgba(76, 175, 80, 0.5)"
GLOW_WARNING = "0 0 12px rgba(255, 193, 7, 0.5)"
GLOW_ERROR = "0 0 12px rgba(244, 67, 54, 0.5)"
GLOW_PRIMARY = "0 0 12px rgba(33, 150, 243, 0.5)"
```

---

### 2.6 动效系统

```python
# 过渡时长 (毫秒)
DURATION_INSTANT = 50    # 立即响应
DURATION_FAST = 150      # 快速交互
DURATION_NORMAL = 250     # 标准动画
DURATION_SLOW = 400       # 强调动画
DURATION_SLOWER = 600     # 大型过渡

# QPropertyAnimation 缓动曲线
from PySide6.QtCore import QEasingCurve

EASE_LINEAR = QEasingCurve.Type.Linear
EASE_IN = QEasingCurve.Type.InCubic
EASE_OUT = QEasingCurve.Type.OutCubic
EASE_IN_OUT = QEasingCurve.Type.InOutCubic
EASE_BOUNCE = QEasingCurve.Type.BezierSpline
```

---

## 三、QSS样式系统

### 3.1 QSS基础样式表

```python
# theme_styles.py - 主题样式定义

DARK_THEME_QSS = """
/* ===========================
   深色主题 (Dark Theme) QSS
   =========================== */

QMainWindow,
QWidget {
    background-color: #0F1419;
    color: #E6EDF3;
    font-family: "Inter", "Segoe UI", sans-serif;
    font-size: 14px;
}

/* 滚动条样式 */
QScrollBar:vertical {
    background: #0F1419;
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #30363D;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #388BFD;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #0F1419;
    height: 10px;
    border: none;
}

QScrollBar::handle:horizontal {
    background: #30363D;
    border-radius: 5px;
    min-width: 30px;
}

/* 标签页样式 */
QTabWidget::pane {
    border: 1px solid #30363D;
    border-radius: 8px;
    background: #161B22;
}

QTabBar::tab {
    background: #161B22;
    color: #8B949E;
    padding: 10px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background: #2196F3;
    color: white;
}

QTabBar::tab:hover {
    background: #21262D;
    color: #E6EDF3;
}
"""

# 完整的主题样式表 - 按钮
BUTTON_QSS = """
/* 主按钮 */
QPushButton[class="primary"] {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
}

QPushButton[class="primary"]:hover {
    background-color: #1E88E5;
}

QPushButton[class="primary"]:pressed {
    background-color: #1976D2;
}

QPushButton[class="primary"]:disabled {
    background-color: #30363D;
    color: #6E7681;
}

/* 次要按钮 */
QPushButton[class="secondary"] {
    background-color: #161B22;
    color: #E6EDF3;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 14px;
}

QPushButton[class="secondary"]:hover {
    background-color: #21262D;
    border-color: #388BFD;
}

/* 危险按钮 */
QPushButton[class="danger"] {
    background-color: #F44336;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
}

QPushButton[class="danger"]:hover {
    background-color: #E53935;
}
"""

# 完整的主题样式表 - 输入框
INPUT_QSS = """
QLineEdit, QTextEdit {
    background-color: #0F1419;
    color: #E6EDF3;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
}

QLineEdit:hover, QTextEdit:hover {
    border-color: #21262D;
}

QLineEdit:focus, QTextEdit:focus {
    border-color: #2196F3;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #161B22;
    color: #6E7681;
}

/* 数值输入框 */
QLineEdit[class="number"] {
    font-family: "JetBrains Mono", "Consolas", monospace;
    text-align: right;
}

/* 组合框 */
QComboBox {
    background-color: #0F1419;
    color: #E6EDF3;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 8px 12px;
}

QComboBox:hover {
    border-color: #388BFD;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: url(://icons/arrow_down.svg);
    width: 12px;
    height: 12px;
}
"""

# 完整的主题样式表 - 表格
TABLE_QSS = """
QTableWidget, QTableView {
    background-color: #0F1419;
    color: #E6EDF3;
    border: 1px solid #30363D;
    border-radius: 8px;
    gridline-color: #21262D;
    font-size: 13px;
}

QTableWidget::item, QTableView::item {
    padding: 8px 12px;
    border-bottom: 1px solid #21262D;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: rgba(33, 150, 243, 0.2);
    color: #E6EDF3;
}

QHeaderView::section {
    background-color: #161B22;
    color: #8B949E;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid #30363D;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 12px;
}

QTableWidget::item:hover, QTableView::item:hover {
    background-color: #21262D;
}
"""

# 完整的主题样式表 - 卡片/面板
CARD_QSS = """
QFrame[class="card"] {
    background-color: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
}

QFrame[class="card"]:hover {
    border-color: #388BFD;
}

/* 数据卡片 */
QFrame[class="data-card"] {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #161B22, stop: 1 #1C2128);
    border: 1px solid #30363D;
    border-radius: 12px;
    border-top: 3px solid qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #2196F3, stop: 1 #00BCD4);
}
"""

# 完整的主题样式表 - 状态徽章
BADGE_QSS = """
QFrame[class="badge-success"] {
    background-color: rgba(76, 175, 80, 0.15);
    border: 1px solid rgba(76, 175, 80, 0.3);
    border-radius: 4px;
    padding: 4px 8px;
}

QFrame[class="badge-warning"] {
    background-color: rgba(255, 193, 7, 0.15);
    border: 1px solid rgba(255, 193, 7, 0.3);
    border-radius: 4px;
    padding: 4px 8px;
}

QFrame[class="badge-error"] {
    background-color: rgba(244, 67, 54, 0.15);
    border: 1px solid rgba(244, 67, 54, 0.3);
    border-radius: 4px;
    padding: 4px 8px;
}
"""
```

---

## 四、组件库实现

### 4.1 主题管理器

```python
# theme_manager.py - PySide6主题管理

from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication
from enum import Enum

class ThemeMode(Enum):
    DARK = "dark"
    LIGHT = "light"

class ThemeManager(QObject):
    """主题管理器 - 单例模式"""

    theme_changed = Signal(str)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._current_theme = ThemeMode.DARK
        self._colors = self._get_dark_colors()

    def _get_dark_colors(self) -> dict:
        return {
            # 背景色
            "bg_base": "#0F1419",
            "bg_raised": "#161B22",
            "bg_overlay": "#1C2128",
            "bg_hover": "#21262D",

            # 文本色
            "text_primary": "#E6EDF3",
            "text_secondary": "#8B949E",
            "text_tertiary": "#6E7681",

            # 边框色
            "border_default": "#30363D",
            "border_muted": "#21262D",
            "border_accent": "#388BFD",

            # 主色
            "primary": "#2196F3",
            "primary_hover": "#1E88E5",

            # 状态色
            "success": "#4CAF50",
            "warning": "#FFC107",
            "error": "#F44336",
            "info": "#2196F3",
        }

    def _get_light_colors(self) -> dict:
        return {
            # 背景色
            "bg_base": "#FFFFFF",
            "bg_raised": "#F6F8FA",
            "bg_overlay": "#FFFFFF",
            "bg_hover": "#F3F4F6",

            # 文本色
            "text_primary": "#1F2937",
            "text_secondary": "#6B7280",
            "text_tertiary": "#9CA3AF",

            # 边框色
            "border_default": "#D1D5DB",
            "border_muted": "#E5E7EB",
            "border_accent": "#2563EB",

            # 主色
            "primary": "#2196F3",
            "primary_hover": "#1E88E5",

            # 状态色
            "success": "#10B981",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "info": "#3B82F6",
        }

    @Slot(str)
    def set_theme(self, theme: str):
        """设置主题"""
        if theme == "light":
            self._current_theme = ThemeMode.LIGHT
            self._colors = self._get_light_colors()
        else:
            self._current_theme = ThemeMode.DARK
            self._colors = self._get_dark_colors()

        self._apply_theme()
        self.theme_changed.emit(theme)

    def _apply_theme(self):
        """应用主题到应用程序"""
        app = QApplication.instance()
        if not app:
            return

        # 设置应用程序调色板
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(self._colors["bg_base"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(self._colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(self._colors["bg_overlay"]))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self._colors["bg_raised"]))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(self._colors["bg_hover"]))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(self._colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(self._colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.Button, QColor(self._colors["bg_raised"]))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self._colors["text_primary"]))
        palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.Link, QColor(self._colors["primary"]))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(self._colors["primary"]))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))

        app.setPalette(palette)

    def get_color(self, key: str) -> str:
        """获取颜色值"""
        return self._colors.get(key, "#000000")

    @Property(str)
    def current_theme(self) -> str:
        return self._current_theme.value

    def get_stylesheet(self, component: str) -> str:
        """获取组件样式表"""
        styles = {
            "button": BUTTON_QSS,
            "input": INPUT_QSS,
            "table": TABLE_QSS,
            "card": CARD_QSS,
            "badge": BADGE_QSS,
        }
        return styles.get(component, "")
```

---

### 4.2 按钮组件

```python
# button.py - 统一按钮组件

from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout
from PySide6.QtCore import Signal, Slot, Property, QTimer
from enum import Enum

class ButtonType(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    GHOST = "ghost"
    DANGER = "danger"
    SUCCESS = "success"

class Button(QPushButton):
    """统一按钮组件"""

    clicked_custom = Signal()  # 自定义点击信号（防抖用）

    def __init__(
        self,
        text: str = "",
        button_type: ButtonType = ButtonType.PRIMARY,
        icon: str = None,
        parent=None
    ):
        super().__init__(text, parent)
        self._button_type = button_type
        self._icon = icon
        self._is_loading = False
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_click)

        self._apply_style()
        self.clicked.connect(self._on_click)

    def _apply_style(self):
        """应用按钮样式"""
        theme = ThemeManager()

        styles = {
            ButtonType.PRIMARY: f"""
                QPushButton {{
                    background-color: {theme.get_color('primary')};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: 500;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {theme.get_color('primary_hover')};
                }}
                QPushButton:pressed {{
                    background-color: #1976D2;
                }}
                QPushButton:disabled {{
                    background-color: #30363D;
                    color: #6E7681;
                }}
            """,
            ButtonType.SECONDARY: f"""
                QPushButton {{
                    background-color: {theme.get_color('bg_raised')};
                    color: {theme.get_color('text_primary')};
                    border: 1px solid {theme.get_color('border_default')};
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {theme.get_color('bg_hover')};
                    border-color: {theme.get_color('border_accent')};
                }}
            """,
            ButtonType.DANGER: f"""
                QPushButton {{
                    background-color: {theme.get_color('error')};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: #E53935;
                }}
            """,
            ButtonType.SUCCESS: f"""
                QPushButton {{
                    background-color: {theme.get_color('success')};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: #43A047;
                }}
            """,
        }

        self.setStyleSheet(styles.get(self._button_type, styles[ButtonType.PRIMARY]))

    def _on_click(self):
        """点击事件处理（防抖）"""
        self._debounce_timer.start(200)  # 200ms防抖

    def _emit_click(self):
        self.clicked_custom.emit()

    def set_loading(self, loading: bool):
        """设置加载状态"""
        self._is_loading = loading
        self.setDisabled(loading)
        if loading:
            self.setText("加载中...")
        else:
            self.setText(self._original_text if hasattr(self, '_original_text') else "")

    @Property(str)
    def button_type(self) -> str:
        return self._button_type.value

    @button_type.setter
    def button_type(self, value: str):
        self._button_type = ButtonType(value)
        self._apply_style()
```

---

### 4.3 数据卡片组件

```python
# data_card.py - 数据展示卡片

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Signal, Property, QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtGui import QFont, QColor, QPalette, QPainter, QLinearGradient, QRadialGradient

class DataCard(QFrame):
    """数据展示卡片组件"""

    def __init__(
        self,
        label: str = "",
        value: str = "0",
        unit: str = "",
        trend: str = "neutral",  # up, down, neutral
        status: str = "normal",  # normal, warning, error
        parent=None
    ):
        super().__init__(parent)
        self._label = label
        self._value = value
        self._unit = unit
        self._trend = trend
        self._status = status

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """设置UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)

        # 顶部状态指示器
        status_bar = QFrame(self)
        status_bar.setFixedHeight(3)
        status_bar.setObjectName("statusBar")

        # 标签行
        label_layout = QHBoxLayout()
        label_layout.setSpacing(8)

        self._label_widget = QLabel(self._label, self)
        self._label_widget.setObjectName("cardLabel")

        status_indicator = QFrame(self)
        status_indicator.setFixedSize(10, 10)
        status_indicator.setObjectName("statusIndicator")
        status_indicator.setStyleSheet("""
            background-color: #4CAF50;
            border-radius: 5px;
        """)

        label_layout.addWidget(self._label_widget)
        label_layout.addStretch()
        label_layout.addWidget(status_indicator)

        # 数值行
        value_layout = QHBoxLayout()
        value_layout.setSpacing(4)

        self._value_widget = QLabel(self._value, self)
        self._value_widget.setObjectName("cardValue")

        self._unit_widget = QLabel(self._unit, self)
        self._unit_widget.setObjectName("cardUnit")

        value_layout.addWidget(self._value_widget)
        value_layout.addWidget(self._unit_widget)
        value_layout.addStretch()

        # 趋势指示
        trend_layout = QHBoxLayout()
        self._trend_widget = QLabel(self._get_trend_symbol(), self)
        self._trend_widget.setObjectName("trendIndicator")

        trend_layout.addWidget(self._trend_widget)
        trend_layout.addStretch()

        layout.addWidget(status_bar)
        layout.addLayout(label_layout)
        layout.addLayout(value_layout)
        layout.addLayout(trend_layout)

    def _get_trend_symbol(self) -> str:
        if self._trend == "up":
            return "↑ 2.5%"
        elif self._trend == "down":
            return "↓ 1.2%"
        return "→ 0%"

    def _apply_style(self):
        theme = ThemeManager()
        colors = theme._colors

        self.setStyleSheet(f"""
            DataCard {{
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {colors['bg_raised']}, stop: 1 {colors['bg_overlay']});
                border: 1px solid {colors['border_default']};
                border-radius: 12px;
                border-top: 3px solid {colors['primary']};
            }}

            DataCard:hover {{
                border-color: {colors['border_accent']};
            }}

            #cardLabel {{
                font-size: 12px;
                color: {colors['text_secondary']};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            #cardValue {{
                font-size: 32px;
                font-weight: bold;
                font-family: "JetBrains Mono", "Consolas", monospace;
                color: {colors['text_primary']};
            }}

            #cardUnit {{
                font-size: 16px;
                color: {colors['text_secondary']};
            }}

            #trendIndicator {{
                font-size: 13px;
                color: {colors['text_secondary']};
            }}
        """)

    def set_value(self, value: str):
        """设置数值"""
        self._value = value
        self._value_widget.setText(value)
        self._animate_value_change()

    def _animate_value_change(self):
        """数值变化动画"""
        anim = QPropertyAnimation(self._value_widget, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(0.5)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()

    def set_status(self, status: str):
        """设置状态（normal/warning/error）"""
        self._status = status
        theme = ThemeManager()
        status_colors = {
            "normal": theme.get_color("success"),
            "warning": theme.get_color("warning"),
            "error": theme.get_color("error"),
        }
        color = status_colors.get(status, status_colors["normal"])
        # 更新状态指示器颜色
```

---

### 4.4 仪表盘组件 (Gauge)

```python
# gauge.py - 圆形仪表盘组件

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, Property, QPropertyAnimation, Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient, QConicalGradient

class Gauge(QFrame):
    """圆形仪表盘组件"""

    value_changed = Signal(float)

    def __init__(
        self,
        min_value: float = 0,
        max_value: float = 100,
        value: float = 0,
        unit: str = "%",
        label: str = "",
        parent=None
    ):
        super().__init__(parent)
        self._min = min_value
        self._max = max_value
        self._value = value
        self._unit = unit
        self._label = label
        self._status = "normal"  # normal, warning, danger

        self.setFixedSize(180, 180)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标签
        self._label_widget = QLabel(self._label, self)
        self._label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label_widget.setStyleSheet("color: #8B949E; font-size: 13px;")

        # 中心数值
        self._value_widget = QLabel(str(self._value), self)
        self._value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_widget.setStyleSheet("""
            color: #E6EDF3;
            font-size: 36px;
            font-weight: bold;
            font-family: "JetBrains Mono", monospace;
        """)

        # 单位
        self._unit_widget = QLabel(self._unit, self)
        self._unit_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._unit_widget.setStyleSheet("color: #8B949E; font-size: 14px;")

    def paintEvent(self, event):
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取颜色
        status_colors = {
            "normal": QColor("#4CAF50"),
            "warning": QColor("#FFC107"),
            "danger": QColor("#F44336"),
        }
        arc_color = status_colors.get(self._status, status_colors["normal"])

        # 计算绘制参数
        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 20
        arc_rect = QRectF(
            center.x() - radius,
            center.y() - radius,
            radius * 2,
            radius * 2
        )

        # 绘制背景弧
        bg_pen = QPen(QColor("#30363D"))
        bg_pen.setWidth(12)
        bg_pen.setCapStyle(Qt.PenCapStyle.Round)
        painter.setPen(bg_pen)
        painter.drawArc(arc_rect, 135 * 16, 270 * 16)

        # 计算进度
        progress = (self._value - self._min) / (self._max - self._min) if self._max > self._min else 0
        span_angle = int(270 * progress * 16)

        # 绘制进度弧
        pen = QPen(arc_color)
        pen.setWidth(12)
        pen.setCapStyle(Qt.PenCapStyle.Round)
        painter.setPen(pen)
        painter.drawArc(arc_rect, 135 * 16, span_angle)

        # 绘制发光效果
        if progress > 0:
            glow_pen = QPen(arc_color)
            glow_pen.setWidth(20)
            glow_pen.setCapStyle(Qt.PenCapStyle.Round)
            glow_pen.setDashPattern([1, 4])
            glow_pen.setColor(QColor(arc_color.red(), arc_color.green(), arc_color.blue(), 50))
            painter.setPen(glow_pen)
            painter.drawArc(arc_rect, 135 * 16, span_angle)

    def set_value(self, value: float, animate: bool = True):
        """设置仪表值"""
        old_value = self._value
        self._value = max(self._min, min(self._max, value))

        if animate:
            self._animate_value(old_value, self._value)
        else:
            self._value_widget.setText(f"{self._value:.1f}")

        self._update_status()
        self.update()
        self.value_changed.emit(self._value)

    def _animate_value(self, from_val: float, to_val: float):
        """数值动画"""
        self._animation = QPropertyAnimation(self, b"gaugeValue")
        self._animation.setDuration(400)
        self._animation.setStartValue(from_val)
        self._animation.setEndValue(to_val)
        self._animation.setEasingCurve(Qt.Curve.OutCubic)
        self._animation.valueChanged.connect(lambda v: self._value_widget.setText(f"{v:.1f}"))
        self._animation.start()

    def _update_status(self):
        """根据数值更新状态"""
        if self._status == "danger":
            return
        ratio = self._value / self._max if self._max > 0 else 0
        if ratio >= 0.9:
            self._status = "danger"
        elif ratio >= 0.7:
            self._status = "warning"
        else:
            self._status = "normal"

    @Property(float)
    def gaugeValue(self) -> float:
        return self._value

    @gaugeValue.setter
    def gaugeValue(self, value: float):
        self._value = value
```

---

### 4.5 状态徽章组件

```python
# status_badge.py - 状态徽章

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Signal, Property
from enum import Enum

class BadgeType(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    NEUTRAL = "neutral"

class StatusBadge(QFrame):
    """状态徽章组件"""

    def __init__(
        self,
        text: str = "",
        badge_type: BadgeType = BadgeType.NEUTRAL,
        show_dot: bool = True,
        pulse: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self._text = text
        self._badge_type = badge_type
        self._show_dot = show_dot
        self._pulse = pulse

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        if self._show_dot:
            self._dot = QLabel(self)
            self._dot.setFixedSize(6, 6)
            self._dot.setObjectName("dot")
            layout.addWidget(self._dot)

        self._text_widget = QLabel(self._text, self)
        self._text_widget.setObjectName("badgeText")
        layout.addWidget(self._text_widget)

    def _apply_style(self):
        theme = ThemeManager()
        colors = {
            BadgeType.SUCCESS: theme.get_color("success"),
            BadgeType.WARNING: theme.get_color("warning"),
            BadgeType.ERROR: theme.get_color("error"),
            BadgeType.INFO: theme.get_color("info"),
            BadgeType.NEUTRAL: theme.get_color("text_secondary"),
        }
        color = colors.get(self._badge_type, colors[BadgeType.NEUTRAL])

        self.setStyleSheet(f"""
            StatusBadge {{
                background-color: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.15);
                border: 1px solid rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.3);
                border-radius: 4px;
            }}

            #dot {{
                background-color: {color};
                border-radius: 3px;
            }}

            #badgeText {{
                color: {color};
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
            }}
        """)

    def set_text(self, text: str):
        self._text = text
        self._text_widget.setText(text)

    def set_badge_type(self, badge_type: BadgeType):
        self._badge_type = badge_type
        self._apply_style()
```

---

### 4.6 Toast通知组件

```python
# toast.py - Toast通知组件

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal, Slot, QTimer, Qt, QPropertyAnimation, Property, QParallelAnimationGroup
from enum import Enum

class ToastType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class Toast(QFrame):
    """Toast通知组件"""

    closed = Signal()

    def __init__(
        self,
        title: str = "",
        message: str = "",
        toast_type: ToastType = ToastType.INFO,
        duration: int = 3000,
        parent=None
    ):
        super().__init__(parent)
        self._title = title
        self._message = message
        self._toast_type = toast_type
        self._duration = duration

        self._setup_ui()
        self._apply_style()
        self._start_auto_close()

    def _setup_ui(self):
        self.setFixedWidth(320)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title_label = QLabel(self._title, self)
        self._title_label.setObjectName("toastTitle")

        close_btn = QPushButton("×", self)
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8B949E;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #E6EDF3;
            }
        """)

        title_layout.addWidget(self._icon_label)
        title_layout.addWidget(self._title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)

        # 消息
        self._message_label = QLabel(self._message, self)
        self._message_label.setObjectName("toastMessage")
        self._message_label.setWordWrap(True)

        layout.addLayout(title_layout)
        layout.addWidget(self._message_label)

    def _apply_style(self):
        theme = ThemeManager()
        type_styles = {
            ToastType.SUCCESS: ("✓", theme.get_color("success")),
            ToastType.ERROR: ("✕", theme.get_color("error")),
            ToastType.WARNING: ("⚠", theme.get_color("warning")),
            ToastType.INFO: ("ℹ", theme.get_color("info")),
        }

        icon, color = type_styles.get(self._toast_type, ("ℹ", theme.get_color("info")))

        self.setStyleSheet(f"""
            Toast {{
                background-color: {theme.get_color('bg_overlay')};
                border: 1px solid {theme.get_color('border_default')};
                border-left: 3px solid {color};
                border-radius: 8px;
            }}

            #toastTitle {{
                color: {theme.get_color('text_primary')};
                font-size: 14px;
                font-weight: 600;
            }}

            #toastMessage {{
                color: {theme.get_color('text_secondary')};
                font-size: 13px;
            }}
        """)

        self._icon_label.setText(f'<span style="color: {color}; font-size: 16px;">{icon}</span>')

    def _start_auto_close(self):
        if self._duration > 0:
            QTimer.singleShot(self._duration, self._animate_close)

    def _animate_close(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(200)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self.close)
        anim.start()

    @Property(float)
    def windowOpacity(self) -> float:
        return self._opacity

    @windowOpacity.setter
    def windowOpacity(self, value: float):
        self._opacity = value
        super().setWindowOpacity(value)


class ToastManager:
    """Toast通知管理器 - 单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._toasts = []
        self._container = None

    def set_container(self, container):
        """设置容器窗口"""
        self._container = container

    def show(self, title: str, message: str, toast_type: ToastType = ToastType.INFO, duration: int = 3000):
        """显示Toast通知"""
        if not self._container:
            return

        toast = Toast(title, message, toast_type, duration, self._container)

        # 计算位置（右上角堆叠）
        x = self._container.width() - toast.width() - 20
        y = 20 + len(self._toasts) * (toast.height() + 10)
        toast.move(x, y)

        toast.closed.connect(lambda: self._remove_toast(toast))
        toast.show()
        self._toasts.append(toast)

    def _remove_toast(self, toast: Toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._relayout_toasts()

    def _relayout_toasts(self):
        """重新排列Toast位置"""
        for i, toast in enumerate(self._toasts):
            x = self._container.width() - toast.width() - 20
            y = 20 + i * (toast.height() + 10)
            toast.move(x, y)
```

---

## 五、布局框架

### 5.1 整体布局结构

```python
# main_layout.py - 主布局框架

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QStackedWidget, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal

class MainLayout(QMainWindow):
    """主布局框架"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_nav()

    def _setup_ui(self):
        """设置UI结构"""
        # 中心窗口部件
        central = QWidget(self)
        self.setCentralWidget(central)

        # 主布局：侧边栏 + 内容区
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        self._sidebar = self._create_sidebar()
        main_layout.addWidget(self._sidebar)

        # 内容区
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 顶部栏
        self._header = self._create_header()
        content_layout.addWidget(self._header)

        # 主内容区（堆叠窗口）
        self._content_stack = QStackedWidget()
        content_layout.addWidget(self._content_stack)

        main_layout.addLayout(content_layout, 1)  # stretch=1

        # 底部状态栏
        self._status_bar = self._create_status_bar()
        content_layout.addWidget(self._status_bar)

    def _create_sidebar(self) -> QFrame:
        """创建侧边栏"""
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0F1419;
                border-right: 1px solid #30363D;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)

        # Logo区域
        logo_frame = QFrame()
        logo_frame.setFixedHeight(64)
        logo_frame.setStyleSheet("""
            border-bottom: 1px solid #21262D;
        """)
        logo_layout = QHBoxLayout(logo_frame)
        logo_layout.setContentsMargins(20, 0, 20, 0)

        logo_icon = QLabel("🎛")
        logo_icon.setStyleSheet("font-size: 24px;")
        logo_title = QLabel("工业监控系统")
        logo_title.setStyleSheet("""
            color: #E6EDF3;
            font-size: 16px;
            font-weight: 600;
        """)
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_title)
        logo_layout.addStretch()

        layout.addWidget(logo_frame)

        # 导航区域
        nav_container = QFrame()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(8, 16, 8, 16)
        nav_layout.setSpacing(4)

        # 添加导航项
        nav_items = [
            ("📊", "数据监控", True),
            ("📋", "设备列表", False),
            ("📈", "历史数据", False),
            ("⚙️", "系统设置", False),
        ]

        for icon, text, active in nav_items:
            nav_item = self._create_nav_item(icon, text, active)
            nav_layout.addWidget(nav_item)

        nav_layout.addStretch()

        layout.addWidget(nav_container)

        return sidebar

    def _create_nav_item(self, icon: str, text: str, active: bool = False) -> QFrame:
        """创建导航项"""
        frame = QFrame()
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {'rgba(33, 150, 243, 0.1)' if active else 'transparent'};
                border-radius: 8px;
                padding: 10px 12px;
            }}
            QFrame:hover {{
                background-color: #21262D;
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")

        text_label = QLabel(text)
        text_label.setStyleSheet(f"""
            color: {'#2196F3' if active else '#E6EDF3'};
            font-size: 14px;
            font-weight: {'600' if active else '400'};
        """)

        layout.addWidget(icon_label)
        layout.addWidget(text_label)

        return frame

    def _create_header(self) -> QFrame:
        """创建顶部栏"""
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border-bottom: 1px solid #30363D;
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        # 页面标题
        title = QLabel("数据监控")
        title.setStyleSheet("""
            color: #E6EDF3;
            font-size: 20px;
            font-weight: 600;
        """)

        layout.addWidget(title)
        layout.addStretch()

        # 操作按钮
        notify_btn = QPushButton("🔔")
        notify_btn.setFixedSize(36, 36)
        notify_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #30363D;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #21262D;
            }
        """)

        user_btn = QPushButton("👤")
        user_btn.setFixedSize(36, 36)
        user_btn.setStyleSheet(notify_btn.styleSheet())

        layout.addWidget(notify_btn)
        layout.addWidget(user_btn)

        return header

    def _create_status_bar(self) -> QFrame:
        """创建底部状态栏"""
        status_bar = QFrame()
        status_bar.setFixedHeight(32)
        status_bar.setStyleSheet("""
            QFrame {
                background-color: #0F1419;
                border-top: 1px solid #30363D;
            }
        """)

        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(16, 0, 16, 0)

        # 连接状态
        status_label = QLabel("● 已连接")
        status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")

        # 在线设备数
        online_label = QLabel("在线: 5/6")
        online_label.setStyleSheet("color: #8B949E; font-size: 12px;")

        # 最后更新时间
        time_label = QLabel("最后更新: 2024-01-15 14:30:25")
        time_label.setStyleSheet("color: #6E7681; font-size: 12px;")

        # 版本
        version_label = QLabel("v2.0.0")
        version_label.setStyleSheet("color: #6E7681; font-size: 12px;")

        layout.addWidget(status_label)
        layout.addWidget(online_label)
        layout.addWidget(time_label)
        layout.addStretch()
        layout.addWidget(version_label)

        return status_bar

    def add_page(self, page: QWidget, index: int = -1):
        """添加页面到内容区"""
        if index < 0:
            index = self._content_stack.count()
        self._content_stack.insertWidget(index, page)

    def set_current_page(self, index: int):
        """设置当前页面"""
        self._content_stack.setCurrentIndex(index)
```

---

## 六、深色主题切换

### 6.1 主题切换实现

```python
# theme_switcher.py - 主题切换组件

from PySide6.QtWidgets import QPushButton, QMenu
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QAction

class ThemeSwitcher(QPushButton):
    """主题切换按钮"""

    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = "dark"

        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 创建菜单
        self._menu = QMenu(self)
        self._menu.addAction("🌙 深色主题", lambda: self._set_theme("dark"))
        self._menu.addAction("☀️ 浅色主题", lambda: self._set_theme("light"))
        self._menu.addAction("⚙️ 系统默认", lambda: self._set_theme("system"))

        self.setMenu(self._menu)
        self._apply_style()

    def _apply_style(self):
        theme = ThemeManager()
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.get_color('bg_raised')};
                border: 1px solid {theme.get_color('border_default')};
                border-radius: 8px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {theme.get_color('bg_hover')};
                border-color: {theme.get_color('border_accent')};
            }}
            QPushButton::menu-indicator {{
                subcontrol-position: bottom-right;
                subcontrol-origin: padding;
                padding: 4px;
            }}
        """)

    @Slot(str)
    def _set_theme(self, theme: str):
        """切换主题"""
        self._current = theme
        ThemeManager().set_theme(theme)
        self._apply_style()
        self.theme_changed.emit(theme)
```

---

## 七、响应式设计

### 7.1 响应式布局实现

```python
# responsive_layout.py - 响应式布局辅助

from PySide6.QtCore import QObject, Signal, Slot, QTimer, Qt
from PySide6.QtWidgets import QWidget, QLayout

class ResponsiveHelper(QObject):
    """响应式布局辅助类"""

    breakpoint_changed = Signal(str)

    # 断点定义
    BREAKPOINTS = {
        "desktop": 1200,
        "tablet": 768,
        "mobile": 0
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_breakpoint = "desktop"
        self._parent = parent

        # 监听窗口大小变化
        if parent:
            parent.resizeEvent = self._on_resize

    def _on_resize(self, event):
        """窗口大小变化处理"""
        width = event.size().width()

        # 确定断点
        if width >= self.BREAKPOINTS["desktop"]:
            new_breakpoint = "desktop"
        elif width >= self.BREAKPOINTS["tablet"]:
            new_breakpoint = "tablet"
        else:
            new_breakpoint = "mobile"

        # 断点变化时发送信号
        if new_breakpoint != self._current_breakpoint:
            self._current_breakpoint = new_breakpoint
            self.breakpoint_changed.emit(new_breakpoint)

    def get_current_breakpoint(self) -> str:
        return self._current_breakpoint

    def is_mobile(self) -> bool:
        return self._current_breakpoint == "mobile"

    def is_tablet(self) -> bool:
        return self._current_breakpoint == "tablet"


def apply_responsive_layout(widget: QWidget, breakpoint: str):
    """根据断点应用不同布局"""
    if breakpoint == "mobile":
        # 移动端：侧边栏隐藏，底部导航
        widget.setContentsMargins(0, 0, 0, 60)  # 底部导航栏
    elif breakpoint == "tablet":
        # 平板：侧边栏折叠
        widget.findChild(QFrame, "sidebar").setFixedWidth(72)
    else:
        # 桌面：完整布局
        widget.findChild(QFrame, "sidebar").setFixedWidth(260)
```

---

## 八、组件应用示例

### 8.1 主窗口集成示例

```python
# main_window.py - 主窗口完整示例

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QFrame, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from theme_manager import ThemeManager, ThemeMode
from button import Button, ButtonType
from data_card import DataCard
from gauge import Gauge
from status_badge import StatusBadge, BadgeType
from toast import ToastManager, ToastType

class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self._theme_manager = ThemeManager()
        self._toast_manager = ToastManager()

        self.setWindowTitle("工业设备管理系统 v2.0")
        self.setMinimumSize(1280, 800)

        # 设置主题
        self._theme_manager.set_theme("dark")

        self._setup_ui()
        self._setup_toast_container()

    def _setup_ui(self):
        """设置UI"""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 页面标题
        title = QLabel("设备监控面板")
        title.setFont(QFont("Inter", 24, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #E6EDF3;")
        layout.addWidget(title)

        # 数据卡片区域
        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        # 温度卡片
        temp_card = DataCard(
            label="温度",
            value="25.5",
            unit="°C",
            trend="up",
            status="normal"
        )
        cards_layout.addWidget(temp_card, 0, 0)

        # 压力卡片
        pressure_card = DataCard(
            label="压力",
            value="1.25",
            unit="MPa",
            trend="neutral",
            status="normal"
        )
        cards_layout.addWidget(pressure_card, 0, 1)

        # 流量卡片
        flow_card = DataCard(
            label="流量",
            value="50.3",
            unit="m³/h",
            trend="down",
            status="warning"
        )
        cards_layout.addWidget(flow_card, 0, 2)

        layout.addLayout(cards_layout)

        # 仪表盘区域
        gauge_layout = QHBoxLayout()
        gauge_layout.setSpacing(24)

        temp_gauge = Gauge(min_value=0, max_value=100, value=45, unit="°C", label="温度")
        pressure_gauge = Gauge(min_value=0, max_value=2, value=1.25, unit="MPa", label="压力")
        power_gauge = Gauge(min_value=0, max_value=100, value=78, unit="kW", label="功率")

        gauge_layout.addWidget(temp_gauge)
        gauge_layout.addWidget(pressure_gauge)
        gauge_layout.addWidget(power_gauge)
        gauge_layout.addStretch()

        layout.addLayout(gauge_layout)

        # 状态徽章区域
        badge_layout = QHBoxLayout()
        badge_layout.setSpacing(12)

        online_badge = StatusBadge("在线", BadgeType.SUCCESS)
        warning_badge = StatusBadge("警告 (3)", BadgeType.WARNING)
        error_badge = StatusBadge("故障 (1)", BadgeType.ERROR)
        info_badge = StatusBadge("维护中", BadgeType.INFO)

        badge_layout.addWidget(online_badge)
        badge_layout.addWidget(warning_badge)
        badge_layout.addWidget(error_badge)
        badge_layout.addWidget(info_badge)
        badge_layout.addStretch()

        layout.addLayout(badge_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        primary_btn = Button("主操作", ButtonType.PRIMARY)
        secondary_btn = Button("次要操作", ButtonType.SECONDARY)
        danger_btn = Button("危险操作", ButtonType.DANGER)
        success_btn = Button("成功操作", ButtonType.SUCCESS)

        primary_btn.clicked_custom.connect(lambda: self._show_toast("操作成功", "主操作已执行", ToastType.SUCCESS))

        btn_layout.addWidget(primary_btn)
        btn_layout.addWidget(secondary_btn)
        btn_layout.addWidget(danger_btn)
        btn_layout.addWidget(success_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        layout.addStretch()

    def _setup_toast_container(self):
        """设置Toast容器"""
        self._toast_manager.set_container(self)

    def _show_toast(self, title: str, message: str, toast_type: ToastType):
        """显示Toast"""
        self._toast_manager.show(title, message, toast_type)


# 入口函数
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 应用全局样式
    theme = ThemeManager()
    app.setStyleSheet(DARK_THEME_QSS + BUTTON_QSS + INPUT_QSS + TABLE_QSS + CARD_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
```

---

## 九、附录：完整样式变量清单

### 9.1 Python颜色常量汇总

```python
# constants.py - 完整颜色和样式常量

# ====================
# 主色
# ====================
COLOR_PRIMARY_50 = "#E3F2FD"
COLOR_PRIMARY_100 = "#BBDEFB"
COLOR_PRIMARY_200 = "#90CAF9"
COLOR_PRIMARY_300 = "#64B5F6"
COLOR_PRIMARY_400 = "#42A5F5"
COLOR_PRIMARY_500 = "#2196F3"  # 基准
COLOR_PRIMARY_600 = "#1E88E5"
COLOR_PRIMARY_700 = "#1976D2"
COLOR_PRIMARY_800 = "#1565C0"
COLOR_PRIMARY_900 = "#0D47A1"

# ====================
# 功能色
# ====================
COLOR_SUCCESS_50 = "#E8F5E9"
COLOR_SUCCESS_100 = "#C8E6C9"
COLOR_SUCCESS_400 = "#66BB6A"
COLOR_SUCCESS_500 = "#4CAF50"  # 成功
COLOR_SUCCESS_600 = "#43A047"

COLOR_WARNING_50 = "#FFF8E1"
COLOR_WARNING_100 = "#FFECB3"
COLOR_WARNING_400 = "#FFCA28"
COLOR_WARNING_500 = "#FFC107"  # 警告
COLOR_WARNING_600 = "#FFB300"

COLOR_ERROR_50 = "#FFEBEE"
COLOR_ERROR_100 = "#FFCDD2"
COLOR_ERROR_400 = "#EF5350"
COLOR_ERROR_500 = "#F44336"  # 错误
COLOR_ERROR_600 = "#E53935"

COLOR_INFO_500 = "#2196F3"  # 信息

# ====================
# 灰度
# ====================
COLOR_GRAY_25 = "#FCFCFD"
COLOR_GRAY_50 = "#F9FAFB"
COLOR_GRAY_100 = "#F3F4F6"
COLOR_GRAY_200 = "#E5E7EB"
COLOR_GRAY_300 = "#D1D5DB"
COLOR_GRAY_400 = "#9CA3AF"
COLOR_GRAY_500 = "#6B7280"
COLOR_GRAY_600 = "#4B5563"
COLOR_GRAY_700 = "#374151"
COLOR_GRAY_800 = "#1F2937"
COLOR_GRAY_900 = "#111827"

# ====================
# 深色主题
# ====================
DARK_BG_BASE = "#0F1419"
DARK_BG_RAISED = "#161B22"
DARK_BG_OVERLAY = "#1C2128"
DARK_BG_HOVER = "#21262D"
DARK_TEXT_PRIMARY = "#E6EDF3"
DARK_TEXT_SECONDARY = "#8B949E"
DARK_TEXT_TERTIARY = "#6E7681"
DARK_BORDER_DEFAULT = "#30363D"
DARK_BORDER_MUTED = "#21262D"
DARK_BORDER_ACCENT = "#388BFD"

# ====================
# 间距
# ====================
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32
SPACE_10 = 40
SPACE_12 = 48
SPACE_16 = 64

# ====================
# 圆角
# ====================
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8
RADIUS_XL = 12
RADIUS_2XL = 16
RADIUS_FULL = 9999

# ====================
# 阴影
# ====================
SHADOW_SM = "0 1px 3px rgba(0, 0, 0, 0.1)"
SHADOW_MD = "0 4px 6px rgba(0, 0, 0, 0.1)"
SHADOW_LG = "0 10px 15px rgba(0, 0, 0, 0.1)"
SHADOW_XL = "0 20px 25px rgba(0, 0, 0, 0.15)"
SHADOW_INDUSTRIAL = "0 4px 12px rgba(33, 150, 243, 0.12)"

# ====================
# 动画时长
# ====================
DURATION_FAST = 150
DURATION_NORMAL = 250
DURATION_SLOW = 400
```

---

**文档版本**: v1.0 (PySide6适配版)
**基于**: UI设计方案 v1.0
**更新日期**: 2026年3月
**技术栈**: PySide6 + Python 3.x
