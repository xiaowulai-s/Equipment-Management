// 工业设备管理系统 - 主界面
// Main View - 基于UI设计方案.md

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
    title: "工业设备管理系统 v1.0"
    background: Rectangle { color: "#0F1419" }

    // ==================== 颜色定义 ====================
    readonly property color colorPrimary: "#2196F3"
    readonly property color colorPrimaryLight: "#42A5F5"
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

    // ==================== 模拟数据 ====================
    property real temperature: 25.5
    property real pressure: 1.23
    property real flowRate: 50.3
    property real power: 15.2
    property real frequency: 50.0
    property real efficiency: 95.2

    property real gauge1Value: 75
    property real gauge2Value: 85
    property real gauge3Value: 90
    property real gauge4Value: 50

    property var tempData: []
    property var pressureData: []
    property var flowData: []

    property string connectionStatus: "已连接"
    property int onlineCount: 5
    property int totalCount: 6
    property string lastUpdate: "2026-03-23 10:30:00"

    // ==================== 定时器 ====================
    Timer {
        id: dataTimer
        interval: 2000
        repeat: true
        onTriggered: updateSimulationData()
    }

    function updateSimulationData() {
        temperature += (Math.random() - 0.5) * 0.5
        temperature = Math.max(20, Math.min(35, temperature))

        pressure += (Math.random() - 0.5) * 0.05
        pressure = Math.max(0.8, Math.min(2.0, pressure))

        flowRate += (Math.random() - 0.5) * 2
        flowRate = Math.max(40, Math.min(60, flowRate))

        power += (Math.random() - 0.5) * 0.5
        power = Math.max(10, Math.min(20, power))

        trendChart.addDataPoint(temperature, pressure, flowRate)

        dataCard1.value = temperature
        dataCard2.value = pressure
        dataCard3.value = flowRate
        dataCard4.value = power

        var now = new Date()
        lastUpdate = now.getFullYear() + "-" +
                     String(now.getMonth() + 1).padStart(2, '0') + "-" +
                     String(now.getDate()).padStart(2, '0') + " " +
                     String(now.getHours()).padStart(2, '0') + ":" +
                     String(now.getMinutes()).padStart(2, '0') + ":" +
                     String(now.getSeconds()).padStart(2, '0')
    }

    // ==================== 侧边栏 ====================
    Rectangle {
        id: sidebar
        width: 260
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: colorBgBase
        border.width: 1
        border.color: colorBorder

        Column {
            anchors.fill: parent

            // Logo区域
            Rectangle {
                height: 64
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                color: colorBgOverlay

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12

                    // Logo图标
                    Rectangle {
                        width: 36
                        height: 36
                        radius: 8
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: colorPrimary }
                            GradientStop { position: 1.0; color: "#00BCD4" }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: "\u2630"
                            color: "white"
                            font.pixelSize: 18
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "工业设备管理"
                        color: textPrimary
                        font.pixelSize: 18
                        font.family: "Inter, sans-serif"
                        font.weight: Font.SemiBold
                    }
                }
            }

            // 导航菜单
            Column {
                anchors.top: parent.top
                anchors.topMargin: 64
                width: parent.width
                spacing: 4
                anchors.leftMargin: 12
                anchors.rightMargin: 12

                // 仪表盘 (选中状态 - 带右侧高亮条)
                Rectangle {
                    width: parent.width
                    height: 40
                    color: Qt.rgba(33/255, 150/255, 243/255, 0.1)
                    radius: 6
                    // 右侧选中指示条
                    Rectangle {
                        anchors.right: parent.right
                        width: 3
                        height: parent.height
                        color: colorPrimary
                        radius: 0
                    }

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        spacing: 12

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "\u25A6"
                            color: colorPrimaryLight
                            font.pixelSize: 16
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "仪表盘"
                            color: colorPrimaryLight
                            font.pixelSize: 15
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Medium
                        }
                    }
                }

                // 其他导航项
                Repeater {
                    model: [
                        { icon: "\u25A9", text: "设备监控" },
                        { icon: "\u2699", text: "设备管理" },
                        { icon: "\u2261", text: "数据分析" },
                        { icon: "\u2630", text: "系统设置" }
                    ]

                    Rectangle {
                        width: parent.width
                        height: 40
                        color: "transparent"
                        radius: 6

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            spacing: 12

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.icon
                                color: textSecondary
                                font.pixelSize: 16
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.text
                                color: textSecondary
                                font.pixelSize: 15
                                font.family: "Inter, sans-serif"
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onEntered: parent.color = colorBgHover
                            onExited: parent.color = "transparent"
                        }
                    }
                }
            }

            // 设备列表区域
            DeviceList {
                anchors.top: parent.top
                anchors.topMargin: 300
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 16
                anchors.leftMargin: 12
                anchors.rightMargin: 12
            }
        }
    }

    // ==================== 主内容区 ====================
    Column {
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        spacing: 16

        // 顶部信息栏
        Rectangle {
            id: topBar
            height: 56
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.topMargin: 16
            color: colorBgRaised
            radius: 8
            border.width: 1
            border.color: colorBorder

            Row {
                anchors.fill: parent
                anchors.margins: 16
                layoutDirection: Qt.RightToLeft
                spacing: 16

                // 主题切换按钮
                Rectangle {
                    width: 36
                    height: 36
                    radius: 6
                    color: colorBgOverlay
                    border.width: 1
                    border.color: colorBorder

                    Text {
                        anchors.centerIn: parent
                        text: "\u263D"
                        color: textSecondary
                        font.pixelSize: 18
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onEntered: parent.color = colorBgHover
                        onExited: parent.color = colorBgOverlay
                    }
                }

                // 连接状态徽章
                Row {
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: colorSuccess

                        // 发光效果
                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 2
                            height: parent.height * 2
                            radius: width / 2
                            color: "transparent"
                            border.width: 1
                            border.color: colorSuccess
                            opacity: 0.5
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: connectionStatus
                        color: colorSuccess
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Medium
                    }
                }

                // 设备标题
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: 16
                    text: "Pump-01 监控面板"
                    color: textPrimary
                    font.pixelSize: 20
                    font.family: "Inter, sans-serif"
                    font.weight: Font.SemiBold
                }
            }
        }

        // 主要内容区域
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: topBar.bottom
            anchors.bottom: statusBar.top
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            color: "transparent"

            Row {
                anchors.fill: parent
                spacing: 16

                // 左侧区域 - 趋势图
                Column {
                    width: 500
                    height: parent.height
                    spacing: 16

                    TrendChart {
                        id: trendChart
                        width: parent.width
                        height: 280
                        chartTitle: "实时趋势"
                        series1Name: "温度"
                        series2Name: "压力"
                        series3Name: "流量"
                        series1Unit: "\u00B0C"
                        series2Unit: "MPa"
                        series3Unit: "m\u00B3/h"
                    }

                    Row {
                        width: parent.width
                        height: 180
                        spacing: 16

                        Gauge {
                            id: gauge1
                            title: "SQ10"
                            value: 75
                            maxValue: 100
                            unit: "%"
                            status: 0
                        }

                        Gauge {
                            id: gauge2
                            title: "AR2"
                            value: 85
                            maxValue: 100
                            unit: "%"
                            status: 1
                        }

                        Gauge {
                            id: gauge3
                            title: "B"
                            value: 90
                            maxValue: 100
                            unit: "%"
                            status: 2
                        }

                        Gauge {
                            id: gauge4
                            title: "C"
                            value: 50
                            maxValue: 100
                            unit: "%"
                            status: 0
                        }
                    }
                }

                // 右侧区域 - 数据卡片和表格
                Column {
                    width: parent.width - 532
                    height: parent.height
                    spacing: 16

                    Row {
                        width: parent.width
                        height: 140
                        spacing: 16

                        DataCard {
                            id: dataCard1
                            label: "温度"
                            value: 25.5
                            unit: "\u00B0C"
                            trend: "up"
                            trendValue: 2.3
                            status: 0
                            decimals: 1
                            width: (parent.width - 48) / 4
                            height: parent.height
                        }

                        DataCard {
                            id: dataCard2
                            label: "压力"
                            value: 1.23
                            unit: "MPa"
                            trend: "down"
                            trendValue: 0.5
                            status: 0
                            decimals: 2
                            width: (parent.width - 48) / 4
                            height: parent.height
                        }

                        DataCard {
                            id: dataCard3
                            label: "流量"
                            value: 50.3
                            unit: "m\u00B3/h"
                            trend: "stable"
                            status: 1
                            decimals: 1
                            width: (parent.width - 48) / 4
                            height: parent.height
                        }

                        DataCard {
                            id: dataCard4
                            label: "功率"
                            value: 15.2
                            unit: "kW"
                            trend: "up"
                            trendValue: 5.1
                            status: 0
                            decimals: 1
                            width: (parent.width - 48) / 4
                            height: parent.height
                        }
                    }

                    ModbusTable {
                        width: parent.width
                        height: parent.height - 156
                    }
                }
            }
        }

        // 底部状态栏
        Rectangle {
            id: statusBar
            height: 32
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.bottomMargin: 16
            color: colorBgRaised
            radius: 6

            Row {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 24

                // 连接状态
                Row {
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: colorSuccess
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "\u2022 已连接"
                        color: colorSuccess
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                    }
                }

                // 分隔线
                Rectangle {
                    width: 1
                    height: 16
                    color: colorBorder
                    anchors.verticalCenter: parent.verticalCenter
                }

                // 在线设备数
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "在线: " + onlineCount + "/" + totalCount
                    color: textSecondary
                    font.pixelSize: 13
                    font.family: "Inter, sans-serif"
                }

                // 分隔线
                Rectangle {
                    width: 1
                    height: 16
                    color: colorBorder
                    anchors.verticalCenter: parent.verticalCenter
                }

                // 最后更新时间
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "最后更新: " + lastUpdate
                    color: textSecondary
                    font.pixelSize: 13
                    font.family: "Inter, sans-serif"
                }

                // 分隔线
                Rectangle {
                    width: 1
                    height: 16
                    color: colorBorder
                    anchors.verticalCenter: parent.verticalCenter
                }

                // 版本信息
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    text: "v1.0.0"
                    color: textTertiary
                    font.pixelSize: 13
                    font.family: "Inter, sans-serif"
                }
            }
        }
    }

    // 启动时开始数据更新
    Component.onCompleted: dataTimer.start()
}