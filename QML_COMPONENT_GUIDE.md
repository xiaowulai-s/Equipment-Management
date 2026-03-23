# QML 组件库使用指南

## 📋 概述

本文档介绍工业设备管理系统的完整QML组件库，这是将HTML/CSS设计系统迁移到PySide6/PyQt5桌面应用的结果。所有组件都遵循Material Design设计原则，并与现有的Theme主题系统完全集成。

---

## 🎨 组件分类

### 1. 核心UI组件 (UILibrary.qml)

#### Button - 按钮组件
用于触发操作或导航。

**属性:**
```qml
Button {
    text: "点击我"
    variant: "primary"      // primary | secondary | ghost | danger | success
    size: "md"              // sm | md | lg
    enabled: true
    loading: false
    
    onClicked: {
        console.log("按钮被点击")
    }
}
```

**变体说明:**
- `primary`: 主要行动按钮，使用品牌色
- `secondary`: 次要按钮，用于辅助操作
- `ghost`: 幽灵按钮，仅显示文本，无背景
- `danger`: 危险操作按钮，使用红色警示
- `success`: 成功操作按钮，使用绿色

**尺寸说明:**
- `sm`: 小号（24px）
- `md`: 中号（36px）
- `lg`: 大号（44px）

---

#### DataCard - 数据卡片
显示单个数值指标的卡片组件。

**属性:**
```qml
DataCard {
    label: "温度"
    value: "25.5"
    unit: "°C"
    status: "online"        // online | offline | warning
    trend: "up"             // up | down | stable
    trendValue: "+2.3%"
}
```

**状态表示:**
- `online`: 绿色亮点，设备在线
- `offline`: 灰色点，设备离线
- `warning`: 橙黄色脉冲，设备告警

**趋势指示:**
- `up`: 向上箭头，数值上升
- `down`: 向下箭头，数值下降
- `stable`: 横线，数值稳定

---

#### Gauge - 仪表盘
显示百分比值的圆形进度表。

**属性:**
```qml
Gauge {
    title: "CPU利用率"
    value: 75               // 0-100
    status: "normal"        // normal | warning | danger
}
```

**状态颜色:**
- `normal`: 蓝色，正常范围
- `warning`: 橙黄色，需要关注
- `danger`: 红色，需要立即处理

---

#### Badge - 状态徽章
用于显示状态标签的小组件。

**属性:**
```qml
Badge {
    status: "success"       // success | warning | error | info | neutral
    text: "正常运行"
    pulse: true             // 是否显示脉冲效果
}
```

**状态类型:**
- `success`: 绿色，表示成功/正常
- `warning`: 橙黄色，表示警告
- `error`: 红色，表示错误
- `info`: 蓝色，表示信息
- `neutral`: 灰色，表示中立

---

### 2. 输入控件 (InputComponents.qml)

#### TextInput - 文本输入框
用于输入单行文本。

**属性:**
```qml
TextInput {
    placeholder: "请输入设备名称"
    text: "原有内容"
    label: "设备名称"
    enabled: true
    helperText: "输入框下方的辅助文本"
    
    onTextChanged: (newText) => {
        console.log("输入内容:", newText)
    }
}
```

---

#### Select - 下拉选择框
用于从预定义选项中选择。

**属性:**
```qml
Select {
    label: "设备类型"
    items: ["温度传感器", "压力传感器", "流量传感器"]
    currentIndex: 0
    
    onSelected: (index, value) => {
        console.log("选择:", value)
    }
}
```

---

#### Checkbox - 复选框
用于多选操作。

**属性:**
```qml
Checkbox {
    text: "启用自动监测"
    checked: false
    
    onToggled: (checked) => {
        console.log("复选框状态:", checked)
    }
}
```

---

#### Toggle - 开关
用于切换两种状态。

**属性:**
```qml
Toggle {
    checked: false
    
    onToggled: (checked) => {
        console.log("开关状态:", checked)
    }
}
```

---

#### ProgressBar - 进度条
显示任务进度。

**属性:**
```qml
ProgressBar {
    value: 0.75             // 0-1
    status: "normal"        // normal | warning | danger
}
```

---

### 3. 导航组件 (NavigationComponents.qml)

#### NavItem - 菜单项
侧边栏或菜单中的项目。

**属性:**
```qml
NavItem {
    label: "概览仪表板"
    icon: "dashboard-icon"
    active: true
    badgeCount: 5           // 0 表示不显示
    
    onClicked: {
        console.log("菜单项被点击")
    }
}
```

---

#### DeviceTreeItem - 设备树项
用于显示可展开的设备层级结构。

**属性:**
```qml
DeviceTreeItem {
    name: "工位A"
    status: "online"        // online | offline | warning
    expanded: false
    isGroup: true           // 是否为分组
    indentLevel: 0          // 缩进级别
    
    onClicked: {
        console.log("项目被点击")
    }
    
    onExpandToggled: (expanded) => {
        console.log("展开状态:", expanded)
    }
}
```

---

#### DataTable - 数据表格
显示表格数据。

**属性:**
```qml
DataTable {
    headers: ["地址", "功能码", "数值", "状态"]
    rows: [
        {address: "0x0001", funcCode: "03", value: "100.5", status: "success"},
        {address: "0x0002", funcCode: "03", value: "85.2", status: "warning"}
    ]
}
```

---

#### DataGrid - 数据网格
网格布局显示数据项。

**属性:**
```qml
DataGrid {
    columns: 2
    items: [
        {label: "在线设备", value: "12"},
        {label: "离线设备", value: "2"},
        {label: "告警数量", value: "3"}
    ]
}
```

---

### 4. 通知反馈 (NotificationComponents.qml)

#### Toast - 吐司通知
短暂显示的通知消息。

**属性:**
```qml
Toast {
    type: "success"         // success | error | warning | info
    message: "操作成功！"
    title: "成功"
    duration: 3000          // 毫秒
    
    onClosed: {
        console.log("通知已关闭")
    }
}
```

---

#### Tooltip - 提示气泡
鼠标悬停时显示的提示。

**属性:**
```qml
Tooltip {
    text: "点击此按钮执行该操作"
    position: "top"         // top | bottom | left | right
}
```

---

#### Loading - 加载指示器
显示加载状态。

**属性:**
```qml
Loading {
    type: "spinner"         // spinner | dots | bar
    message: "加载中..."
}
```

---

#### DialogButtons - 对话框按钮组
对话框中的确认/取消按钮。

**属性:**
```qml
DialogButtons {
    primaryText: "确认"
    secondaryText: "取消"
    
    onPrimaryClicked: {
        console.log("确认")
    }
    
    onSecondaryClicked: {
        console.log("取消")
    }
}
```

---

### 5. 数据可视化 (ChartComponents.qml)

#### TrendChart - 趋势折线图
显示时间序列数据的折线图。

**属性:**
```qml
TrendChart {
    title: "温度趋势"
    dataPoints: [
        {x: 0, y: 20},
        {x: 1, y: 22},
        {x: 2, y: 25},
        {x: 3, y: 23}
    ]
    minValue: 0
    maxValue: 100
    maxPoints: 60           // 最多显示点数
    theme: "light"          // light | dark
}
```

**方法:**
```qml
// 添加新数据点
trendChart.addDataPoint(25.5)

// 清空所有数据
trendChart.clearData()
```

---

#### BarChart - 柱状图
显示分类数据的柱状图。

**属性:**
```qml
BarChart {
    title: "设备统计"
    data: [
        {label: "温度传感器", value: 30},
        {label: "压力传感器", value: 25},
        {label: "流量传感器", value: 20}
    ]
    maxValue: 100
}
```

---

## 🎯 主题系统

所有组件都使用 `Theme` 对象中的颜色属性，确保外观一致性。

### 颜色分类

**主色系 (Primary Colors):**
```
primary50-900: 蓝色系 10 个等级
accent400-600: 青色系补充色
```

**语义色:**
```
success: 绿色，表示成功
warning: 橙黄色，表示警告
error: 红色，表示错误
info: 蓝色，表示信息
```

**中性色:**
```
gray25-900: 灰色系 11 个等级
```

**背景色:**
```
bgBase: 基础背景色（白色）
bgRaised: 抬升背景色（浅灰）
bgOverlay: 覆盖色（半透明黑）
bgHover: 悬停背景色（浅灰）
```

### 在QML中使用主题

```qml
import "./components/" as Components

Rectangle {
    color: Theme.bgBase
    
    Text {
        color: Theme.textPrimary
        font.pixelSize: 14
    }
    
    rectangle {
        color: Theme.primary500
        border.color: Theme.borderDefault
    }
}
```

---

## 💡 常见用法

### 1. 创建仪表板卡片布局

```qml
import QtQuick 2.15
import QtQuick.Layouts 1.15
import "./components/UILibrary.js" as UILib

Rectangle {
    RowLayout {
        spacing: 16
        
        UILib.DataCard {
            label: "温度"
            value: "25.5"
            unit: "°C"
            status: "online"
        }
        
        UILib.DataCard {
            label: "压力"
            value: "85.2"
            unit: "kPa"
            status: "warning"
        }
        
        UILib.DataCard {
            label: "流量"
            value: "12.3"
            unit: "L/s"
            status: "online"
        }
    }
}
```

### 2. 创建表单

```qml
Column {
    spacing: 16
    
    InputComponents.TextInput {
        placeholder: "设备名称"
        label: "名称"
    }
    
    InputComponents.Select {
        label: "类型"
        items: ["类型A", "类型B", "类型C"]
    }
    
    InputComponents.Checkbox {
        text: "启用监测"
    }
    
    UILib.Button {
        text: "保存"
        variant: "primary"
        onClicked: {
            // 保存操作
        }
    }
}
```

### 3. 实现带通知的操作

```qml
function performAction() {
    // 显示加载状态
    loadingIndicator.visible = true
    
    // 执行操作
    timer.setTimeout(() => {
        loadingIndicator.visible = false
        
        // 显示成功通知
        toastComponent.createObject(parent, {
            type: "success",
            message: "操作成功！"
        })
    }, 1000)
}
```

### 4. 创建设备监控列表

```qml
Column {
    NavItem {
        label: "设备管理"
        active: true
    }
    
    Repeater {
        model: deviceList
        
        DeviceTreeItem {
            name: modelData.name
            status: modelData.status
            isGroup: modelData.isGroup
            indentLevel: modelData.level
        }
    }
}
```

---

## 📦 文件结构

```
qml/
├── MainView.qml                    # 主应用窗口
├── Theme.qml                       # 主题常量定义
├── ComponentPreview.qml            # 组件预览页面
├── components/
│   ├── UILibrary.qml              # 核心UI组件库
│   ├── InputComponents.qml        # 输入控件组件库
│   ├── NavigationComponents.qml   # 导航和列表组件库
│   ├── NotificationComponents.qml # 通知反馈组件库
│   ├── ChartComponents.qml        # 数据可视化组件库
│   ├── Button.qml                 # 原始按钮（可选，已在UILibrary中）
│   ├── DataCard.qml               # 原始数据卡片（可选，已在UILibrary中）
│   ├── Gauge.qml                  # 原始仪表盘（可选，已在UILibrary中）
│   ├── StatusBadge.qml            # 原始状态徽章（可选，已在UILibrary中）
│   ├── TrendChart.qml             # 原始趋势图（可选，已在ChartComponents中）
│   ├── ModbusTable.qml            # 原始Modbus表格（可选，已在NavigationComponents中）
│   └── DeviceList.qml             # 原始设备列表（可选，已在NavigationComponents中）
```

---

## 🔧 集成到主应用

### 步骤 1: 在 MainView.qml 中导入主题

```qml
import "./Theme.js" as Theme
```

### 步骤 2: 引入组件库

```qml
import "./components/UILibrary.qml" as UILib
import "./components/InputComponents.qml" as InputCtl
import "./components/NavigationComponents.qml" as NavCtl
```

### 步骤 3: 在UI中使用组件

```qml
UILib.Button {
    text: "执行操作"
    onClicked: doSomething()
}
```

---

## 📱 响应式设计

所有组件都支持响应式设计。使用 `Layout.fillWidth` 和 `Layout.fillHeight` 创建适应性布局：

```qml
RowLayout {
    anchors.fill: parent
    
    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        // 内容会自动拉伸
    }
}
```

---

## ❌ 常见错误排查

### 1. 组件显示不正确
- 检查 Theme 对象是否正确导入
- 确保颜色属性名称拼写正确

### 2. 事件不响应
- 确保 MouseArea 的 anchors 正确设置
- 检查 propagateComposedEvents 属性

### 3. 动画不流畅
- 检查持续时间（duration）是否合理
- 确保使用了恰当的缓动函数（easing）

---

## 🎉 总结

本组件库提供了完整的UI构建块，适用于工业设备管理系统的各种场景。通过遵循主题系统和设计原则，可以快速构建一致、专业的用户界面。

有问题？请参考 ComponentPreview.qml 中的完整示例！
