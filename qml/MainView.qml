import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 1280
    height: 800
    minimumWidth: 1024
    minimumHeight: 600
    title: "工业设备管理系统 v1.0.1"
    background: Rectangle { color: "#0F1419" }

    // 颜色定义 - 来自Theme
    readonly property color colorPrimary: "#2196F3"
    readonly property color colorPrimaryLight: "#42A5F5"
    readonly property color colorAccent: "#00BCD4"
    readonly property color colorSuccess: "#4CAF50"
    readonly property color colorWarning: "#FFC107"
    readonly property color colorError: "#F44336"
    readonly property color colorBgBase: "#0F1419"
    readonly property color colorBgRaised: "#161B22"
    readonly property color colorBgOverlay: "#1C2128"
    readonly property color colorBgHover: "#21262D"
    readonly property color colorBgActive: "#30363D"
    readonly property color colorBorder: "#30363D"
    readonly property color colorBorderAccent: "#388BFD"
    readonly property color textPrimary: "#E6EDF3"
    readonly property color textSecondary: "#8B949E"
    readonly property color textTertiary: "#6E7681"

    // 绑定后端数据
    property real temperature: backend ? backend.temperature : 25.5
    property real pressure: backend ? backend.pressure : 1.23
    property real flowRate: backend ? backend.flowRate : 50.3
    property real power: backend ? backend.power : 15.2
    property real frequency: backend ? backend.frequency : 50.0
    property real efficiency: backend ? backend.efficiency : 95.2

    property real gauge1Value: 75
    property real gauge2Value: 85
    property real gauge3Value: 90
    property real gauge4Value: 50

    property var tempData: backend ? backend.get_temperature_data() : []
    property var pressureData: backend ? backend.get_pressure_data() : []
    property var flowData: backend ? backend.get_flow_data() : []

    property string connectionStatus: backend ? backend.connectionStatus : "未连接"
    property int onlineCount: backend ? backend.onlineCount : 5
    property int totalCount: backend ? backend.totalCount : 6
    property string lastUpdate: backend ? backend.lastUpdate : "2026-03-23 10:30:00"

    // 激活的导航项
    property int activeNavIndex: 0

    // 导航项数据
    property var navItems: [
        { icon: "dashboard", text: "仪表盘", badge: "" },
        { icon: "monitor", text: "设备监控", badge: "6" },
        { icon: "settings", text: "设备管理", badge: "" },
        { icon: "chart", text: "数据分析", badge: "" },
        { icon: "config", text: "系统设置", badge: "" }
    ]

    // 监听后端信号
    Connections {
        target: backend

        onTemperatureChanged: {
            temperature = backend.temperature
        }

        onPressureChanged: {
            pressure = backend.pressure
            updateDataCards()
            updateTrendChart()
        }

        onFlowRateChanged: {
            flowRate = backend.flowRate
        }

        onPowerChanged: {
            power = backend.power
            updateDataCards()
        }

        onFrequencyChanged: {
            frequency = backend.frequency
        }

        onEfficiencyChanged: {
            efficiency = backend.efficiency
        }

        onGauge1Changed: {
            var val = backend ? backend.gauge1Value : 0
            gauge1Value = (val !== undefined && val !== null) ? val : 0
            if (gauge1) gauge1.value = gauge1Value
        }

        onGauge2Changed: {
            var val = backend ? backend.gauge2Value : 0
            gauge2Value = (val !== undefined && val !== null) ? val : 0
            if (gauge2) gauge2.value = gauge2Value
        }

        onGauge3Changed: {
            var val = backend ? backend.gauge3Value : 0
            gauge3Value = (val !== undefined && val !== null) ? val : 0
            if (gauge3) gauge3.value = gauge3Value
        }

        onGauge4Changed: {
            var val = backend ? backend.gauge4Value : 0
            gauge4Value = (val !== undefined && val !== null) ? val : 0
            if (gauge4) gauge4.value = gauge4Value
        }

        onConnectionStatusChanged: {
            connectionStatus = backend.connectionStatus
        }

        onOnlineCountChanged: {
            onlineCount = backend.onlineCount
        }

        onTotalCountChanged: {
            totalCount = backend.totalCount
        }

        onLastUpdateChanged: {
            lastUpdate = backend.lastUpdate
        }

        onTrendDataChanged: {
            trendChart.series1Data = tempData
            trendChart.series2Data = pressureData
            trendChart.series3Data = flowData
        }

        onSystemMessage: function(msgType, message) {
            showNotification(msgType, message)
        }
    }

    // 更新数据卡片
    function updateDataCards() {
        if (dataCard1) dataCard1.value = temperature
        if (dataCard2) dataCard2.value = pressure
        if (dataCard3) dataCard3.value = flowRate
        if (dataCard4) dataCard4.value = power
    }

    // 更新趋势图
    function updateTrendChart() {
        if (trendChart) {
            trendChart.addDataPoint(temperature, pressure, flowRate)
        }
    }

    // 显示通知
    function showNotification(type, message) {
        notificationComponent.createObject(mainWindow, {
            "notificationType": type,
            "notificationMessage": message
        })
    }

    // 启动监控
    Component.onCompleted: {
        if (backend) {
            backend.start_monitoring()
        }
    }

    Rectangle {
        id: sidebar
        width: 240
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: colorBgBase
        border.width: 1
        border.color: colorBorder

        Rectangle {
            id: logoArea
            height: 60
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            color: colorBgOverlay

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                // Logo图标
                Rectangle {
                    width: 32
                    height: 32
                    radius: 6
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: colorPrimary }
                        GradientStop { position: 1.0; color: colorAccent }
                    }

                    Canvas {
                        anchors.centerIn: parent
                        width: 18
                        height: 18

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)
                            ctx.strokeStyle = "white"
                            ctx.lineWidth = 2
                            ctx.lineCap = "round"
                            ctx.lineJoin = "round"

                            ctx.beginPath()
                            ctx.moveTo(9, 1)
                            ctx.lineTo(1, 6)
                            ctx.lineTo(9, 11)
                            ctx.lineTo(17, 6)
                            ctx.closePath()
                            ctx.stroke()

                            ctx.beginPath()
                            ctx.moveTo(1, 11)
                            ctx.lineTo(9, 16)
                            ctx.lineTo(17, 11)
                            ctx.stroke()
                        }
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "设备管理"
                    color: textPrimary
                    font.pixelSize: 16
                    font.family: "Inter, sans-serif"
                    font.weight: Font.Bold
                }
            }
        }

        Column {
            id: navColumn
            anchors.top: logoArea.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 12
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            spacing: 2

            // 导航项
            Repeater {
                model: navItems.length

                Rectangle {
                    width: parent.width
                    height: 38
                    radius: 6
                    color: activeNavIndex === index ? Qt.rgba(33/255, 150/255, 243/255, 0.15) : "transparent"

                    Rectangle {
                        anchors.right: parent.right
                        width: 3
                        height: parent.height
                        color: colorPrimary
                        radius: 0
                        visible: activeNavIndex === index
                    }

                    Row {
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 10

                        Canvas {
                            id: navIcon
                            width: 18
                            height: 18
                            anchors.verticalCenter: parent.verticalCenter

                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.clearRect(0, 0, width, height)
                                ctx.strokeStyle = activeNavIndex === index ? colorPrimaryLight : textSecondary
                                ctx.lineWidth = 1.8
                                ctx.lineCap = "round"
                                ctx.lineJoin = "round"

                                var icon = navItems[index].icon

                                if (icon === "dashboard") {
                                    ctx.strokeRect(1, 1, 7, 7)
                                    ctx.strokeRect(10, 1, 7, 7)
                                    ctx.strokeRect(1, 10, 7, 7)
                                    ctx.strokeRect(10, 10, 7, 7)
                                } else if (icon === "monitor") {
                                    ctx.strokeRect(1, 2, 16, 11)
                                    ctx.moveTo(6, 16)
                                    ctx.lineTo(12, 16)
                                    ctx.moveTo(9, 13)
                                    ctx.lineTo(9, 16)
                                } else if (icon === "settings") {
                                    ctx.beginPath()
                                    ctx.arc(9, 9, 3, 0, Math.PI * 2)
                                    ctx.stroke()
                                    ctx.moveTo(9, 1)
                                    ctx.lineTo(9, 3)
                                    ctx.moveTo(9, 15)
                                    ctx.lineTo(9, 17)
                                    ctx.moveTo(1, 9)
                                    ctx.lineTo(3, 9)
                                    ctx.moveTo(15, 9)
                                    ctx.lineTo(17, 9)
                                    ctx.moveTo(3, 3)
                                    ctx.lineTo(4.5, 4.5)
                                    ctx.moveTo(12.5, 12.5)
                                    ctx.lineTo(14, 14)
                                    ctx.moveTo(3, 15)
                                    ctx.lineTo(4.5, 13.5)
                                    ctx.moveTo(12.5, 4.5)
                                    ctx.lineTo(14, 3)
                                } else if (icon === "chart") {
                                    ctx.moveTo(1, 17)
                                    ctx.lineTo(1, 11)
                                    ctx.lineTo(5, 11)
                                    ctx.lineTo(5, 17)
                                    ctx.moveTo(7, 17)
                                    ctx.lineTo(7, 5)
                                    ctx.lineTo(11, 5)
                                    ctx.lineTo(11, 17)
                                    ctx.moveTo(13, 17)
                                    ctx.lineTo(13, 9)
                                    ctx.lineTo(17, 9)
                                    ctx.lineTo(17, 17)
                                } else if (icon === "config") {
                                    ctx.strokeRect(1, 6, 16, 8)
                                    ctx.beginPath()
                                    ctx.arc(6, 10, 3, 0, Math.PI * 2)
                                    ctx.stroke()
                                    ctx.beginPath()
                                    ctx.arc(12, 10, 3, 0, Math.PI * 2)
                                    ctx.stroke()
                                }
                            }
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: navItems[index].text
                            color: activeNavIndex === index ? colorPrimaryLight : textSecondary
                            font.pixelSize: 14
                            font.family: "Inter, sans-serif"
                        }

                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.rightMargin: 6
                            height: 18
                            radius: 9
                            color: colorError
                            visible: navItems[index].badge !== ""

                            Text {
                                anchors.centerIn: parent
                                text: navItems[index].badge
                                color: "white"
                                font.pixelSize: 10
                                font.family: "Inter, sans-serif"
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onEntered: {
                            if (activeNavIndex !== index) {
                                parent.color = colorBgHover
                            }
                        }
                        onExited: {
                            if (activeNavIndex !== index) {
                                parent.color = "transparent"
                            }
                        }
                        onClicked: {
                            activeNavIndex = index
                            pageView.currentIndex = index
                        }
                    }
                }
            }
        }

        // 设备列表区域
        Rectangle {
            id: deviceListContainer
            anchors.top: navColumn.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.topMargin: 12
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.bottomMargin: 12
            clip: true

            DeviceList {
                id: deviceList
                anchors.fill: parent
            }
        }
    }

    // 主内容区
    Column {
        id: mainContent
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        anchors.topMargin: 12
        anchors.bottomMargin: 12
        spacing: 12

        Rectangle {
            id: topBar
            height: 52
            width: parent.width
            color: colorBgRaised
            radius: 8
            border.width: 1
            border.color: colorBorder

            Row {
                width: parent.width
                height: parent.height
                spacing: 16

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 16
                    text: {
                        activeNavIndex === 0 ? "Pump-01 监控面板" :
                        activeNavIndex === 1 ? "设备监控" :
                        activeNavIndex === 2 ? "设备管理" :
                        activeNavIndex === 3 ? "数据分析" :
                        "系统设置"
                    }
                    color: textPrimary
                    font.pixelSize: 18
                    font.family: "Inter, sans-serif"
                }

                Item {
                    width: parent.width - 300 // 固定宽度偏移
                    height: 1
                }

                Row {
                    spacing: 8
                    anchors.rightMargin: 16

                    // 连接状态指示灯
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: connectionStatus === "已连接" ? colorSuccess : colorError

                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 2
                            height: parent.height * 2
                            radius: width / 2
                            color: "transparent"
                            border.width: 1
                            border.color: connectionStatus === "已连接" ? colorSuccess : colorError
                            opacity: 0.5
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: connectionStatus
                        color: connectionStatus === "已连接" ? colorSuccess : colorError
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                    }
                }

                // 主题切换按钮
                Button {
                    isIconButton: true
                    iconSource: "theme"
                    buttonStyleName: "ghost"
                    size: "md"
                    onClicked: {
                        // 主题切换功能
                    }
                }
            }
        }

        // 页面切换区域
        SwipeView {
            id: pageView
            width: parent.width
            height: parent.height - 52 - 28 - 12
            currentIndex: activeNavIndex
            interactive: true
            clip: true

            // 页面1: 监控仪表盘
            Item {
                id: dashboardPage
                width: parent.width
                height: parent.height

                Row {
                    anchors.fill: parent
                    spacing: 12

                    // 左侧列 - 图表和仪表盘
                    Column {
                        width: 480
                        height: parent.height
                        spacing: 12

                        TrendChart {
                            id: trendChart
                            width: parent.width
                            height: 260
                            chartTitle: "实时趋势"
                            series1Name: "温度"
                            series2Name: "压力"
                            series3Name: "流量"
                            series1Unit: "\u00B0C"
                            series2Unit: "MPa"
                            series3Unit: "m\u00B3/h"
                        }

                        // 仪表盘行
                        Row {
                            width: parent.width
                            height: 170
                            spacing: 10

                            Gauge {
                                id: gauge1
                                title: "SQ10"
                                value: gauge1Value
                                maxValue: 100
                                unit: "%"
                                status: 0
                                width: (parent.width - 30) / 4
                                height: parent.height
                            }

                            Gauge {
                                id: gauge2
                                title: "AR2"
                                value: gauge2Value
                                maxValue: 100
                                unit: "%"
                                status: 1
                                width: (parent.width - 30) / 4
                                height: parent.height
                            }

                            Gauge {
                                id: gauge3
                                title: "B"
                                value: gauge3Value
                                maxValue: 100
                                unit: "%"
                                status: 2
                                width: (parent.width - 30) / 4
                                height: parent.height
                            }

                            Gauge {
                                id: gauge4
                                title: "C"
                                value: gauge4Value
                                maxValue: 100
                                unit: "%"
                                status: 0
                                width: (parent.width - 30) / 4
                                height: parent.height
                            }
                        }
                    }

                    // 右侧列 - 数据卡片和表格
                    Column {
                        width: parent.width - 492
                        height: parent.height
                        spacing: 12

                        // 数据卡片行
                        Row {
                            width: parent.width
                            height: 130
                            spacing: 10

                            DataCard {
                                id: dataCard1
                                label: "温度"
                                value: temperature
                                unit: "\u00B0C"
                                trend: "up"
                                trendValue: 2.3
                                status: 0
                                decimals: 1
                                width: (parent.width - 30) / 4
                                height: parent.height
                            }

                            DataCard {
                                id: dataCard2
                                label: "压力"
                                value: pressure
                                unit: "MPa"
                                trend: "down"
                                trendValue: 0.5
                                status: 0
                                decimals: 2
                                width: (parent.width - 30) / 4
                                height: parent.height
                            }

                            DataCard {
                                id: dataCard3
                                label: "流量"
                                value: flowRate
                                unit: "m\u00B3/h"
                                trend: "stable"
                                status: 1
                                decimals: 1
                                width: (parent.width - 30) / 4
                                height: parent.height
                            }

                            DataCard {
                                id: dataCard4
                                label: "功率"
                                value: power
                                unit: "kW"
                                trend: "up"
                                trendValue: 5.1
                                status: 0
                                decimals: 1
                                width: (parent.width - 30) / 4
                                height: parent.height
                            }
                        }

                        // Modbus表格
                        ModbusTable {
                            id: modbusTable
                            width: parent.width
                            height: parent.height - 130 - 12
                        }
                    }
                }
            }

            // 页面2: 设备监控
            Item {
                id: deviceMonitorPage
                width: parent.width
                height: parent.height

                Column {
                    anchors.fill: parent
                    spacing: 12

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.verticalCenter: parent.verticalCenter
                        text: "设备监控页面"
                        color: textPrimary
                        font.pixelSize: 20
                        font.family: "Inter, sans-serif"
                    }
                }
            }

            // 页面3: 设备管理
            Item {
                id: deviceManagementPage
                width: parent.width
                height: parent.height

                Column {
                    anchors.fill: parent
                    spacing: 12

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.verticalCenter: parent.verticalCenter
                        text: "设备管理页面"
                        color: textPrimary
                        font.pixelSize: 20
                        font.family: "Inter, sans-serif"
                    }
                }
            }

            // 页面4: 数据分析
            Item {
                id: dataAnalysisPage
                width: parent.width
                height: parent.height

                DataExport {
                    anchors.fill: parent
                    anchors.margins: 12
                }
            }

            // 页面5: 系统设置
            Item {
                id: systemSettingsPage
                width: parent.width
                height: parent.height

                ConfigManagement {
                    anchors.fill: parent
                    anchors.margins: 12
                }
            }

            // 监听页面切换
            onCurrentIndexChanged: {
                activeNavIndex = currentIndex
            }
        }

        // 状态栏
        Rectangle {
            id: statusBar
            height: 28
            width: parent.width
            color: colorBgRaised
            radius: 6

            Row {
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 20

                Row {
                    spacing: 6
                    anchors.verticalCenter: parent.verticalCenter

                    Canvas {
                        width: 8
                        height: 8
                        anchors.verticalCenter: parent.verticalCenter

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)
                            ctx.fillStyle = connectionStatus === "已连接" ? colorSuccess : colorError
                            ctx.beginPath()
                            ctx.arc(4, 4, 3, 0, Math.PI * 2)
                            ctx.fill()
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: connectionStatus
                        color: connectionStatus === "已连接" ? colorSuccess : colorError
                        font.pixelSize: 12
                        font.family: "Inter, sans-serif"
                    }
                }

                Rectangle {
                    width: 1
                    height: 14
                    color: colorBorder
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "在线: " + onlineCount + "/" + totalCount
                    color: textSecondary
                    font.pixelSize: 12
                    font.family: "Inter, sans-serif"
                }

                Rectangle {
                    width: 1
                    height: 14
                    color: colorBorder
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "最后更新: " + lastUpdate
                    color: textSecondary
                    font.pixelSize: 12
                    font.family: "Inter, sans-serif"
                }

                Item {
                    Layout.fillWidth: true
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "v1.0.1"
                    color: textTertiary
                    font.pixelSize: 12
                    font.family: "Inter, sans-serif"
                }
            }
        }
    }

    // 通知组件
    Component {
        id: notificationComponent
        Rectangle {
            property string notificationType: "info"
            property string notificationMessage: ""

            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 20
            anchors.rightMargin: 20
            width: 300
            height: 60
            radius: 8
            color: notificationType === "success" ? "#4CAF50" :
                   notificationType === "error" ? "#F44336" :
                   notificationType === "warning" ? "#FFC107" : "#2196F3"

            Text {
                anchors.centerIn: parent
                text: notificationMessage
                color: "white"
                font.pixelSize: 14
                font.family: "Inter, sans-serif"
            }

            // 3秒后自动消失
            Timer {
                interval: 3000
                onTriggered: parent.destroy()
            }
        }
    }
}
