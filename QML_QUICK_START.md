# QML 组件库 - 快速开始指南（5分钟入门）

## 🎯 5分钟快速入门

### 第1步：了解你拥有什么

你现在有 **5 个专业的 QML 组件库**：

```
📦 qml/components/
├── UILibrary.qml              ← 核心 UI 组件（Button, DataCard, Gauge, Badge）
├── InputComponents.qml        ← 输入控件（TextInput, Select, Checkbox, Toggle）
├── NavigationComponents.qml   ← 导航组件（NavItem, DeviceTreeItem, Table, Grid）
├── NotificationComponents.qml ← 反馈组件（Toast, Tooltip, Loading, Dialog）
└── ChartComponents.qml        ← 图表组件（TrendChart, BarChart）
```

### 第2步：选择你需要的组件

在任何 QML 文件中导入组件库：

```qml
// 方式1：导入整个库
import "./components/UILibrary.qml" as UI

// 方式2：导入特定库
import "./components/InputComponents.qml" as Input
import "./components/NavigationComponents.qml" as Nav
```

### 第3步：使用组件

最简单的例子：

```qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import "./components/UILibrary.qml" as UI

ApplicationWindow {
    visible: true
    
    UI.Button {
        text: "点击我"
        onClicked: print("Hello, QML Components!")
    }
}
```

保存并运行 - 您会看到一个漂亮的蓝色按钮！

---

## 📚 10个常用示例

### 示例 1：显示数据卡片

```qml
UI.DataCard {
    label: "温度"
    value: "25.5"
    unit: "°C"
    status: "online"  // online, offline, warning
}
```

### 示例 2：多个按钮

```qml
Row {
    spacing: 8
    
    UI.Button {
        text: "确认"
        variant: "primary"
    }
    
    UI.Button {
        text: "取消"
        variant: "secondary"
    }
    
    UI.Button {
        text: "删除"
        variant: "danger"
    }
}
```

### 示例 3：文本输入框

```qml
import "./components/InputComponents.qml" as Input

Input.TextInput {
    placeholder: "请输入"
    label: "设备名称"
}
```

### 示例 4：复选框

```qml
import "./components/InputComponents.qml" as Input

Input.CheckBox {
    text: "同意条款"
    checked: false
}
```

### 示例 5：开关

```qml
import "./components/InputComponents.qml" as Input

Row {
    spacing: 12
    
    Input.Toggle {
        id: myToggle
    }
    
    Text {
        text: myToggle.checked ? "启用" : "禁用"
    }
}
```

### 示例 6：仪表盘

```qml
UI.Gauge {
    title: "CPU利用率"
    value: 75  // 0-100
    status: "normal"  // normal, warning, danger
}
```

### 示例 7：菜单项（侧边栏）

```qml
import "./components/NavigationComponents.qml" as Nav

Column {
    Nav.NavItem {
        label: "仪表板"
        active: true
    }
    
    Nav.NavItem {
        label: "设备管理"
    }
}
```

### 示例 8：吐司通知

```qml
import "./components/NotificationComponents.qml" as Notify

Button {
    text: "显示通知"
    onClicked: {
        var toast = notifyComponent.createObject(parent, {
            type: "success",
            message: "操作成功！"
        })
    }
}

Component {
    id: notifyComponent
    Notify.Toast {}
}
```

### 示例 9：数据表格

```qml
import "./components/NavigationComponents.qml" as Nav

Nav.DataTable {
    headers: ["名字", "值", "状态"]
    rows: [
        {address: "温度", funcCode: "传感器", value: "25°C", status: "success"},
        {address: "压力", funcCode: "传感器", value: "85kPa", status: "warning"}
    ]
}
```

### 示例 10：趋势图

```qml
import "./components/ChartComponents.qml" as Charts

Charts.TrendChart {
    title: "温度趋势"
    minValue: 0
    maxValue: 100
    
    Component.onCompleted: {
        // 添加数据点
        addDataPoint(20)
        addDataPoint(25)
        addDataPoint(30)
    }
}
```

---

## 🎨 主题和颜色

### 使用主题颜色

所有组件都支持 Theme 对象。在 QML 中：

```qml
import "./Theme.js" as Theme

Rectangle {
    color: Theme.bgBase           // 白色背景
    
    Text {
        color: Theme.textPrimary  // 深灰色文字
    }
    
    UI.Button {
        // 自动使用 Theme.primary500 作为按钮色
    }
}
```

### 常用颜色

```javascript
// 主色系
Theme.primary500      // 品牌蓝色
Theme.accent500      // 补充青色

// 语义色
Theme.success500     // 绿色（成功）
Theme.warning500     // 橙色（警告）
Theme.error500       // 红色（错误）

// 背景色
Theme.bgBase         // 白色
Theme.bgRaised       // 浅灰
Theme.bgHover        // 鼠标悬停灰色

// 文字色
Theme.textPrimary    // 正文
Theme.textSecondary  // 次要
Theme.textTertiary   // 辅助

// 边框色
Theme.borderDefault  // 标准边框
```

---

## 🔗 完整的表单示例

```qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "./components/UILibrary.qml" as UI
import "./components/InputComponents.qml" as Input

Rectangle {
    width: 400
    height: 500
    color: "#f5f5f5"
    
    Column {
        anchors { fill: parent; margins: 24 }
        spacing: 16
        
        // 标题
        Text {
            text: "设备编辑表单"
            font.pixelSize: 24
            font.weight: Font.Bold
        }
        
        // 设备名称
        Input.TextInput {
            label: "设备名称"
            placeholder: "请输入设备名称"
        }
        
        // 设备类型
        Input.Select {
            label: "设备类型"
            items: ["温度传感器", "压力传感器", "流量传感器"]
        }
        
        // 启用选项
        Input.CheckBox {
            text: "启用设备"
            checked: true
        }
        
        Item { height: 16 }
        
        // 按钮组
        Row {
            spacing: 12
            
            UI.Button {
                text: "保存"
                variant: "primary"
                onClicked: print("保存设备信息")
            }
            
            UI.Button {
                text: "取消"
                variant: "secondary"
                onClicked: print("取消编辑")
            }
        }
        
        Item { Layout.fillHeight: true }
    }
}
```

---

## 🎯 性能提示

### ✅ 推荐做法

```qml
// ✓ 好：及时创建和销毁
Component {
    id: toastComponent
    Toast {}
}

Button {
    onClicked: {
        var toast = toastComponent.createObject(parent)
        toast.destroy(3000)  // 3秒后销毁
    }
}

// ✓ 好：使用 Repeater 处理列表
ListView {
    delegate: DataCard {
        label: model.label
        value: model.value
    }
}
```

### ❌ 避免做法

```qml
// ✗ 不好：在 mouseArea 中创建大量对象
MouseArea {
    onClicked: {
        var obj = component.createObject(parent)
        // 没有销毁！
    }
}

// ✗ 不好：频繁修改 anchors
onPositionChanged: {
    anchors.x = x  // 性能杀手
}
```

---

## 🐛 常见问题速查

### Q: 组件不显示？

**A:** 检查：
1. 是否导入了 QtQuick 2.15？
2. 是否正确导入了组件库？
3. 是否设置了 width/height 或使用了 anchors？

```qml
// 正确的最小例子
import QtQuick 2.15
import "./components/UILibrary.qml" as UI

ApplicationWindow {  // ← 或 Rectangle，需要有顶级窗口
    visible: true
    width: 400
    height: 300
    
    UI.Button {
        anchors.centerIn: parent  // ← 必须设置位置
        text: "看我"
    }
}
```

### Q: 组件颜色不对？

**A:** 检查 Theme 定义是否加载：

```qml
import "./Theme.js" as Theme

Rectangle {
    color: Theme.bgBase  // ← 确保 Theme 正确导入
}
```

### Q: 如何响应用户交互？

**A:** 使用信号和槽：

```qml
UI.Button {
    text: "我可以被点击"
    
    onClicked: {
        console.log("按钮被点击了！")
        doSomething()
    }
}

Input.TextInput {
    onTextChanged: {
        console.log("当前输入：" + inputValue)
    }
}
```

### Q: 组件滚动显示不全？

**A:** 使用 ScrollView：

```qml
import QtQuick.Controls

ScrollView {
    anchors.fill: parent
    
    Column {
        spacing: 16
        
        // 你的组件在这里
        UI.DataCard { }
        UI.DataCard { }
        UI.DataCard { }
    }
}
```

---

## 📖 后续学习

### 🔰 初级（快速开始）
- ✅ 现在：5分钟快速开始（本文件）
- 📖 下一步：QML_COMPONENT_GUIDE.md（完整指南）

### 🎓 中级（深度学习）
- 📖 QML_COMPONENT_INTEGRATION.md（集成到应用）
- 👁️ ComponentPreview.qml（完整示例应用）

### 🚀 高级（定制开发）
- 🛠️ 修改组件库源代码
- 📝 创建自定义组件
- 🔌 与 Python 后端集成

---

## 📞 需要更多帮助？

1. **快速查找**: 用 Ctrl+F 在本文件中搜索
2. **完整文档**: 查看 QML_COMPONENT_GUIDE.md
3. **实际例子**: 运行 ComponentPreview.qml
4. **代码示例**: 查看各组件库源代码中的注释

---

## ✨ 记住的要点

| 要点 | 说明 |
|------|------|
| **导入** | `import "./components/XXX.qml" as XX` |
| **创建** | 直接在 QML 中声明组件 |
| **属性** | 通过 `property: value` 配置 |
| **事件** | 使用 `onXXX: { }` 处理 |
| **样式** | 自动使用 Theme 主题 |
| **响应式** | 使用 Layout 布局系统 |

---

🎉 **现在你已准备好开始构建专业应用了！**

有问题？参考完整文档或源代码中的注释！
