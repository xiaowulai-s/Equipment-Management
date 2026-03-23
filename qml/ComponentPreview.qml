// 工业设备管理系统 - QML 组件预览页面

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "./components/UILibrary.js" as UILib

ApplicationWindow {
    id: previewWindow
    visible: true
    width: 1280
    height: 800
    title: "工业设备管理系统 - QML UI 预览"
    color: Theme.bgBase
    
    // 引入主题
    property var Theme: ({
        // 主色系 - 蓝色系
        primary50: "#E3F2FD",
        primary100: "#BBDEFB",
        primary200: "#90CAF9",
        primary300: "#64B5F6",
        primary400: "#42A5F5",
        primary500: "#2196F3",
        primary600: "#1E88E5",
        primary700: "#1976D2",
        primary800: "#1565C0",
        primary900: "#0D47A1",
        
        // 补充色 - 青色系
        accent400: "#26C6DA",
        accent500: "#00BCD4",
        accent600: "#00ACC1",
        
        // 语义色
        success400: "#66BB6A",
        success500: "#4CAF50",
        success600: "#43A047",
        success50: "#E8F5E9",
        
        warning400: "#FFA726",
        warning500: "#FF9800",
        warning600: "#F57C00",
        warning50: "#FFF3E0",
        
        error400: "#EF5350",
        error500: "#F44336",
        error600: "#E53935",
        error50: "#FFEBEE",
        
        info400: "#29B6F6",
        info500: "#03A9F4",
        info600: "#0288D1",
        info50: "#E1F5FE",
        
        // 中性色 - 灰色系
        gray25: "#FAFAFB",
        gray50: "#F9FAFB",
        gray100: "#F3F4F6",
        gray200: "#E5E7EB",
        gray300: "#D1D5DB",
        gray400: "#9CA3AF",
        gray500: "#6B7280",
        gray600: "#4B5563",
        gray700: "#374151",
        gray800: "#1F2937",
        gray900: "#111827",
        
        // 背景色
        bgBase: "#FFFFFF",
        bgRaised: "#F9FAFB",
        bgOverlay: "rgba(0, 0, 0, 0.5)",
        bgHover: "#F3F4F6",
        
        // 文字色
        textPrimary: "#111827",
        textSecondary: "#4B5563",
        textTertiary: "#6B7280",
        
        // 边框色
        borderDefault: "#E5E7EB",
        borderMuted: "#F3F4F6",
        borderAccent: "#2196F3",
        
        space1: 4,
        space2: 8,
        space3: 12,
        space4: 16,
        space6: 24,
        space8: 32
    })
    
    RowLayout {
        anchors.fill: parent
        spacing: 0
        
        // ============ 左侧导航栏 ============
        Rectangle {
            Layout.width: 260
            Layout.fillHeight: true
            color: Theme.bgRaised
            border.right: Border { color: Theme.borderDefault; width: 1 }
            
            ScrollView {
                anchors.fill: parent
                
                Column {
                    width: parent.width
                    spacing: 0
                    
                    // Logo
                    Rectangle {
                        width: parent.width
                        height: 80
                        color: Theme.primary500
                        
                        Column {
                            anchors.centerIn: parent
                            spacing: 4
                            horizontalAlignment: Column.AlignHCenter
                            
                            Text {
                                text: "设备管理"
                                color: "white"
                                font.pixelSize: 20
                                font.weight: Font.Bold
                            }
                            
                            Text {
                                text: "QML 组件库"
                                color: "rgba(255, 255, 255, 0.7)"
                                font.pixelSize: 12
                            }
                        }
                    }
                    
                    // 导航菜单
                    NavItem {
                        label: "UI 库组件"
                        active: true
                        onClicked: contentLoader.sourceComponent = uiLibraryView
                    }
                    
                    NavItem {
                        label: "输入控件"
                        onClicked: contentLoader.sourceComponent = inputControlsView
                    }
                    
                    NavItem {
                        label: "导航组件"
                        onClicked: contentLoader.sourceComponent = navigationView
                    }
                    
                    NavItem {
                        label: "通知反馈"
                        onClicked: contentLoader.sourceComponent = notificationView
                    }
                    
                    NavItem {
                        label: "图表组件"
                        onClicked: contentLoader.sourceComponent = chartView
                    }
                }
            }
        }
        
        // ============ 右侧内容区 ============
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.bgBase
            
            Loader {
                id: contentLoader
                anchors { fill: parent; margins: 24 }
                sourceComponent: uiLibraryView
            }
        }
    }
    
    // ============ 导航菜单项组件 ============
    Component {
        id: navItemComponent
        
        Rectangle {
            id: navItem
            property string label: ""
            property bool active: false
            
            signal clicked()
            
            width: 260
            height: 44
            color: active ? Theme.primary50 : "transparent"
            
            Text {
                anchors { left: parent.left; leftMargin: 20; verticalCenter: parent.verticalCenter }
                text: parent.label
                color: parent.active ? Theme.primary600 : Theme.textPrimary
                font.pixelSize: 14
                font.weight: parent.active ? Font.Medium : Font.Normal
            }
            
            Rectangle {
                width: 3
                height: parent.height
                color: parent.active ? Theme.primary600 : "transparent"
                anchors.right: parent.right
            }
            
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    navItem.clicked()
                }
            }
        }
    }
    
    Component {
        id: navItem
        NavItemComponent {}
    }
    
    // ============ 视图：UI 库组件 ============
    Component {
        id: uiLibraryView
        
        ScrollView {
            width: contentLoader.width
            height: contentLoader.height
            
            Column {
                width: parent.width
                spacing: 24
                
                Text {
                    text: "UI 库核心组件"
                    color: Theme.textPrimary
                    font.pixelSize: 24
                    font.weight: Font.Bold
                }
                
                // 按钮组件演示
                GroupBox {
                    title: "按钮 (Button)"
                    width: parent.width
                    
                    RowLayout {
                        anchors.fill: parent
                        spacing: 12
                        
                        // 主按钮
                        Rectangle {
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 36
                            radius: 6
                            color: Theme.primary500
                            
                            Text {
                                anchors.centerIn: parent
                                text: "主按钮"
                                color: "white"
                                font.pixelSize: 14
                                font.weight: Font.Medium
                            }
                            
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                onEntered: parent.color = Theme.primary600
                                onExited: parent.color = Theme.primary500
                            }
                        }
                        
                        // 次按钮
                        Rectangle {
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 36
                            radius: 6
                            color: Theme.bgRaised
                            border { color: Theme.borderDefault; width: 1 }
                            
                            Text {
                                anchors.centerIn: parent
                                text: "次按钮"
                                color: Theme.textPrimary
                                font.pixelSize: 14
                            }
                            
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                onEntered: parent.color = Theme.bgHover
                                onExited: parent.color = Theme.bgRaised
                            }
                        }
                        
                        // 危险按钮
                        Rectangle {
                            Layout.preferredWidth: 100
                            Layout.preferredHeight: 36
                            radius: 6
                            color: Theme.error500
                            
                            Text {
                                anchors.centerIn: parent
                                text: "危险操作"
                                color: "white"
                                font.pixelSize: 14
                                font.weight: Font.Medium
                            }
                            
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                onEntered: parent.color = Theme.error600
                                onExited: parent.color = Theme.error500
                            }
                        }
                        
                        Item {
                            Layout.fillWidth: true
                        }
                    }
                }
                
                // 数据卡片演示
                GroupBox {
                    title: "数据卡片 (DataCard)"
                    width: parent.width
                    
                    RowLayout {
                        anchors.fill: parent
                        spacing: 16
                        
                        DataCardPreview {
                            label: "温度"
                            value: "25.5"
                            unit: "°C"
                            status: "online"
                        }
                        
                        DataCardPreview {
                            label: "压力"
                            value: "85.2"
                            unit: "kPa"
                            status: "warning"
                        }
                        
                        DataCardPreview {
                            label: "流量"
                            value: "12.3"
                            unit: "L/s"
                            status: "online"
                        }
                        
                        Item {
                            Layout.fillWidth: true
                        }
                    }
                }
                
                Item {
                    height: 100
                }
            }
        }
    }
    
    // ============ 视图：输入控件 ============
    Component {
        id: inputControlsView
        
        ScrollView {
            width: contentLoader.width
            height: contentLoader.height
            
            Column {
                width: parent.width
                spacing: 24
                
                Text {
                    text: "输入控件组件"
                    color: Theme.textPrimary
                    font.pixelSize: 24
                    font.weight: Font.Bold
                }
                
                GroupBox {
                    title: "文本输入框 (TextInput)"
                    width: parent.width
                    
                    TextInputPreview {
                        placeholder: "请输入设备名称"
                        label: "设备名称"
                    }
                }
                
                GroupBox {
                    title: "复选框 (Checkbox)"
                    width: parent.width
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        
                        CheckboxPreview {
                            text: "启用自动监测"
                        }
                        
                        CheckboxPreview {
                            text: "启用告警推送"
                        }
                    }
                }
                
                GroupBox {
                    title: "开关 (Toggle)"
                    width: parent.width
                    
                    RowLayout {
                        anchors.fill: parent
                        spacing: 16
                        
                        TogglePreview {}
                        
                        Text {
                            text: "启用实时监测"
                            color: Theme.textSecondary
                            font.pixelSize: 14
                        }
                        
                        Item {
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }
    }
    
    // ============ 视图：导航组件 ============
    Component {
        id: navigationView
        
        ScrollView {
            width: contentLoader.width
            height: contentLoader.height
            
            Column {
                width: parent.width
                spacing: 24
                
                Text {
                    text: "导航和列表组件"
                    color: Theme.textPrimary
                    font.pixelSize: 24
                    font.weight: Font.Bold
                }
                
                GroupBox {
                    title: "菜单项 (NavItem)"
                    width: parent.width
                    height: 200
                    
                    Column {
                        anchors.fill: parent
                        spacing: 0
                        
                        NavItemPreview {
                            label: "概览仪表板"
                            active: true
                        }
                        
                        NavItemPreview {
                            label: "设备管理"
                        }
                        
                        NavItemPreview {
                            label: "数据统计"
                            badgeCount: 5
                        }
                    }
                }
                
                GroupBox {
                    title: "设备树项 (DeviceTreeItem)"
                    width: parent.width
                    height: 200
                    
                    Column {
                        anchors.fill: parent
                        spacing: 0
                        
                        DeviceTreeItemPreview {
                            name: "工位A"
                            isGroup: true
                            status: "online"
                        }
                        
                        DeviceTreeItemPreview {
                            name: "温度传感器"
                            indentLevel: 1
                            status: "online"
                        }
                        
                        DeviceTreeItemPreview {
                            name: "压力传感器"
                            indentLevel: 1
                            status: "warning"
                        }
                    }
                }
            }
        }
    }
    
    // ============ 视图：通知反馈 ============
    Component {
        id: notificationView
        
        ScrollView {
            width: contentLoader.width
            height: contentLoader.height
            
            Column {
                width: parent.width
                spacing: 24
                
                Text {
                    text: "通知和反馈组件"
                    color: Theme.textPrimary
                    font.pixelSize: 24
                    font.weight: Font.Bold
                }
                
                GroupBox {
                    title: "吐司通知 (Toast)"
                    width: parent.width
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12
                        
                        ToastPreview {
                            type: "success"
                            message: "操作成功"
                        }
                        
                        ToastPreview {
                            type: "error"
                            message: "操作失败，请重试"
                        }
                        
                        ToastPreview {
                            type: "warning"
                            message: "警告：设备温度过高"
                        }
                        
                        ToastPreview {
                            type: "info"
                            message: "信息提示：系统已更新"
                        }
                    }
                }
            }
        }
    }
    
    // ============ 视图：图表组件 ============
    Component {
        id: chartView
        
        ScrollView {
            width: contentLoader.width
            height: contentLoader.height
            
            Column {
                width: parent.width
                spacing: 24
                
                Text {
                    text: "数据可视化组件"
                    color: Theme.textPrimary
                    font.pixelSize: 24
                    font.weight: Font.Bold
                }
                
                GroupBox {
                    title: "趋势图 (TrendChart)"
                    width: parent.width
                    height: 280
                    
                    TrendChartPreview {
                        title: "温度趋势"
                    }
                }
            }
        }
    }
    
    // ============ 预览组件 ============
    
    Component {
        id: dataCardPreview
        
        Rectangle {
            id: card
            property string label: ""
            property string value: ""
            property string unit: ""
            property string status: "online"
            
            Layout.preferredWidth: 200
            Layout.preferredHeight: 140
            radius: 8
            color: Theme.bgRaised
            border { color: Theme.borderDefault; width: 1 }
            
            Rectangle {
                width: parent.width
                height: 4
                color: card.status === "online" ? Theme.success500 :
                       card.status === "warning" ? Theme.warning500 :
                       Theme.gray300
                radius: card.radius
                anchors { top: parent.top; left: parent.left; right: parent.right }
            }
            
            Column {
                anchors { fill: parent; margins: 12 }
                spacing: 8
                
                Text {
                    text: card.label
                    color: Theme.textSecondary
                    font.pixelSize: 12
                }
                
                Row {
                    spacing: 4
                    
                    Text {
                        text: card.value
                        color: Theme.textPrimary
                        font.pixelSize: 24
                        font.weight: Font.Bold
                    }
                    
                    Text {
                        text: card.unit
                        color: Theme.textSecondary
                        font.pixelSize: 12
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 2
                    }
                }
                
                Item { height: 1 }
                
                Row {
                    spacing: 6
                    
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: card.status === "online" ? Theme.success500 :
                               card.status === "warning" ? Theme.warning500 :
                               Theme.gray300
                    }
                    
                    Text {
                        text: card.status === "online" ? "在线" : 
                              card.status === "warning" ? "告警" : "离线"
                        color: Theme.textTertiary
                        font.pixelSize: 12
                    }
                }
            }
        }
    }
    
    Component {
        id: textInputPreview
        
        Rectangle {
            id: inputBox
            property string placeholder: ""
            property string label: ""
            
            width: parent.width
            height: 70
            color: "transparent"
            
            Column {
                anchors.fill: parent
                spacing: 6
                
                Text {
                    text: inputBox.label
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }
                
                Rectangle {
                    width: parent.width
                    height: 36
                    radius: 6
                    color: Theme.bgRaised
                    border { color: Theme.borderDefault; width: 1 }
                    
                    TextInput {
                        anchors { fill: parent; margins: 8 }
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        
                        Text {
                            anchors { fill: parent; margins: 8 }
                            text: inputBox.placeholder
                            color: Theme.textTertiary
                            visible: !parent.text
                        }
                    }
                }
            }
        }
    }
    
    Component {
        id: checkboxPreview
        
        Rectangle {
            id: cb
            property string text: ""
            property bool checked: false
            
            width: parent.width
            height: 28
            color: "transparent"
            
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                
                Rectangle {
                    width: 18
                    height: 18
                    radius: 4
                    color: cb.checked ? Theme.primary500 : "transparent"
                    border { color: Theme.borderDefault; width: 2 }
                }
                
                Text {
                    text: cb.text
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            
            MouseArea {
                anchors.fill: parent
                onClicked: cb.checked = !cb.checked
            }
        }
    }
    
    Component {
        id: togglePreview
        
        Rectangle {
            width: 44
            height: 24
            radius: 12
            color: Theme.primary500
            
            Rectangle {
                width: 20
                height: 20
                radius: 10
                color: "white"
                x: 22
                y: 2
            }
        }
    }
    
    Component {
        id: navItemPreview
        
        Rectangle {
            id: ni
            property string label: ""
            property bool active: false
            property int badgeCount: 0
            
            width: parent.width
            height: 44
            color: active ? Theme.primary50 : "transparent"
            
            Row {
                anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                spacing: 10
                
                Rectangle {
                    width: 24
                    height: 24
                    radius: 4
                    color: Theme.gray200
                    anchors.verticalCenter: parent.verticalCenter
                }
                
                Text {
                    text: ni.label
                    color: ni.active ? Theme.primary600 : Theme.textPrimary
                    font.pixelSize: 14
                    font.weight: ni.active ? Font.Medium : Font.Normal
                    Layout.fillWidth: true
                    anchors.verticalCenter: parent.verticalCenter
                }
                
                Rectangle {
                    visible: ni.badgeCount > 0
                    width: 24
                    height: 24
                    radius: 12
                    color: Theme.error500
                    anchors.verticalCenter: parent.verticalCenter
                    
                    Text {
                        anchors.centerIn: parent
                        text: ni.badgeCount
                        color: "white"
                        font.pixelSize: 12
                        font.weight: Font.Bold
                    }
                }
            }
        }
    }
    
    Component {
        id: deviceTreeItemPreview
        
        Rectangle {
            id: dti
            property string name: ""
            property int indentLevel: 0
            property string status: "online"
            property bool isGroup: false
            
            width: parent.width
            height: 36
            color: "transparent"
            
            Row {
                anchors { fill: parent; margins: 4 }
                leftMargin: 12 + (dti.indentLevel * 16)
                spacing: 8
                
                Rectangle {
                    width: 12
                    height: 12
                    radius: 6
                    color: dti.status === "offline" ? Theme.gray300 :
                           dti.status === "warning" ? Theme.warning400 :
                           Theme.success500
                    anchors.verticalCenter: parent.verticalCenter
                }
                
                Text {
                    text: dti.name
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    font.weight: dti.isGroup ? Font.Medium : Font.Normal
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
    
    Component {
        id: toastPreview
        
        Rectangle {
            id: toast
            property string type: "success"
            property string message: ""
            
            width: parent.width
            height: 60
            radius: 8
            color: toast.type === "success" ? Theme.success50 :
                   toast.type === "error" ? Theme.error50 :
                   toast.type === "warning" ? Theme.warning50 :
                   Theme.info50
            border {
                width: 1
                color: toast.type === "success" ? Theme.success200 :
                       toast.type === "error" ? Theme.error200 :
                       toast.type === "warning" ? Theme.warning200 :
                       Theme.info200
            }
            
            Rectangle {
                width: 3
                height: parent.height
                radius: parent.radius
                color: toast.type === "success" ? Theme.success500 :
                       toast.type === "error" ? Theme.error500 :
                       toast.type === "warning" ? Theme.warning500 :
                       Theme.info500
            }
            
            Row {
                anchors { fill: parent; margins: 12; leftMargin: 16 }
                spacing: 12
                
                Rectangle {
                    width: 24
                    height: 24
                    radius: 4
                    color: Toast.type === "success" ? Theme.success500 :
                           Toast.type === "error" ? Theme.error500 :
                           Toast.type === "warning" ? Theme.warning500 :
                           Theme.info500
                }
                
                Text {
                    text: toast.message
                    color: toast.type === "success" ? Theme.success700 :
                           toast.type === "error" ? Theme.error700 :
                           toast.type === "warning" ? Theme.warning700 :
                           Theme.info700
                    font.pixelSize: 13
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
    
    Component {
        id: trendChartPreview
        
        Rectangle {
            id: chart
            property string title: ""
            
            width: parent.width
            height: parent.height
            color: Theme.bgBase
            border {
                color: Theme.borderDefault
                width: 1
            }
            radius: 8
            
            Column {
                anchors { fill: parent; margins: 16 }
                spacing: 16
                
                Text {
                    text: chart.title
                    color: Theme.textPrimary
                    font.pixelSize: 16
                    font.weight: Font.Medium
                }
                
                Rectangle {
                    width: parent.width
                    height: 200
                    color: Theme.bgRaised
                    radius: 6
                    
                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            var padding = 30
                            var w = width
                            var h = height
                            
                            // 网格线
                            ctx.strokeStyle = Theme.borderDefault
                            ctx.lineWidth = 1
                            for (var i = 0; i <= 4; i++) {
                                var y = padding + (h - 2*padding)/4 * i
                                ctx.beginPath()
                                ctx.moveTo(padding, y)
                                ctx.lineTo(w - padding, y)
                                ctx.stroke()
                            }
                            
                            // Y轴标签
                            ctx.fillStyle = Theme.textTertiary
                            ctx.font = "12px Inter"
                            ctx.textAlign = "right"
                            for (var i = 0; i <= 4; i++) {
                                var val = 100 - 25*i
                                var y = padding + (h - 2*padding)/4 * i
                                ctx.fillText(val, padding - 5, y + 4)
                            }
                            
                            // 曲线
                            ctx.strokeStyle = Theme.accent500
                            ctx.lineWidth = 2
                            ctx.beginPath()
                            ctx.moveTo(padding, h - padding - 60)
                            ctx.quadraticCurveTo(w/3, h - padding - 80, w/2, h - padding - 40)
                            ctx.quadraticCurveTo(2*w/3, h - padding - 20, w - padding, h - padding - 50)
                            ctx.stroke()
                        }
                    }
                }
            }
        }
    }
}
