// 工业设备管理系统 - 主界面
// Main View

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
    background: themeManager.bgBase

    ThemeManager {
        id: themeManager
    }

    Toast {
        id: toast
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 16
        anchors.rightMargin: 16
        z: 1000
    }

    ModalDialog {
        id: modalDialog
        anchors.fill: parent
        modal: true
    }

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
    property string lastUpdate: "2026-03-23 09:47:00"
    property bool deviceRunning: false

    Timer {
        id: dataTimer
        interval: 2000
        repeat: true
        onTriggered: {
            updateSimulationData()
        }
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

        gauge1.value = gauge1Value
        gauge2.value = gauge2Value
        gauge3.value = gauge3Value
        gauge4.value = gauge4Value

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

    function showToast(type, title, message) {
        toast.show(type, title, message)
    }

    function handleDeviceStart() {
        deviceRunning = true
        controlPanel.setRunning(true)
        controlPanel.setLoading(false)
        showToast("success", "操作成功", "设备启动成功")
    }

    function handleDeviceStop() {
        deviceRunning = false
        controlPanel.setRunning(false)
        controlPanel.setLoading(false)
        showToast("info", "设备停止", "设备已停止运行")
    }

    function handleDeviceReset() {
        controlPanel.setLoading(false)
        showToast("warning", "设备复位", "设备已复位")
    }

    Rectangle {
        id: sidebar
        width: 260
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: themeManager.bgRaised
        border.width: 1
        border.color: themeManager.borderDefault

        Column {
            anchors.fill: parent

            Rectangle {
                height: 64
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                color: themeManager.bgOverlay

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: themeManager.space5
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: themeManager.space3

                    Rectangle {
                        width: 36
                        height: 36
                        radius: themeManager.radiusLg
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: themeManager.primary500 }
                            GradientStop { position: 1.0; color: themeManager.accent500 }
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
                        color: themeManager.textPrimary
                        font.pixelSize: themeManager.fontH4
                        font.family: themeManager.fontSans
                        font.weight: Font.SemiBold
                    }
                }
            }

            Column {
                anchors.top: parent.top
                anchors.topMargin: 64
                width: parent.width
                spacing: themeManager.space1

                Rectangle {
                    width: parent.width
                    height: 40
                    color: themeManager.primary500 + "20"
                    radius: themeManager.radiusMd

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: themeManager.space5
                        spacing: themeManager.space3

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "\u25A6"
                            color: themeManager.primary400
                            font.pixelSize: 16
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "仪表盘"
                            color: themeManager.primary400
                            font.pixelSize: themeManager.fontBody
                            font.family: themeManager.fontSans
                            font.weight: Font.Medium
                        }
                    }
                }

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
                        radius: themeManager.radiusMd

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: themeManager.space5
                            spacing: themeManager.space3

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.icon
                                color: themeManager.textSecondary
                                font.pixelSize: 16
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.text
                                color: themeManager.textSecondary
                                font.pixelSize: themeManager.fontBody
                                font.family: themeManager.fontSans
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onEntered: parent.color = themeManager.bgHover
                            onExited: parent.color = "transparent"
                        }
                    }
                }
            }

            Rectangle {
                anchors.top: parent.top
                anchors.topMargin: 300
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: themeManager.space4
                color: "transparent"

                DeviceList {
                    id: deviceList
                    anchors.fill: parent
                }
            }
        }
    }

    Column {
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        spacing: themeManager.space4

        Rectangle {
            id: topBar
            height: 56
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: themeManager.space4
            anchors.rightMargin: themeManager.space4
            anchors.topMargin: themeManager.space4
            color: themeManager.bgRaised
            radius: themeManager.radiusLg
            border.width: 1
            border.color: themeManager.borderDefault

            Row {
                anchors.fill: parent
                anchors.margins: themeManager.space4
                layoutDirection: Qt.RightToLeft
                spacing: themeManager.space4

                Rectangle {
                    width: 36
                    height: 36
                    radius: themeManager.radiusMd
                    color: themeManager.bgOverlay
                    border.width: 1
                    border.color: themeManager.borderDefault

                    Text {
                        id: themeIcon
                        anchors.centerIn: parent
                        text: "\u2600"
                        color: themeManager.textSecondary
                        font.pixelSize: 18
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            themeManager.toggleTheme()
                            if (themeManager.isDarkTheme) {
                                themeIcon.text = "\u2600"
                            } else {
                                themeIcon.text = "\u263E"
                            }
                            showToast("info", "主题切换", themeManager.isDarkTheme ? "已切换到深色主题" : "已切换到浅色主题")
                        }
                    }
                }

                Row {
                    spacing: themeManager.space2
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: themeManager.success500
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: connectionStatus
                        color: themeManager.success500
                        font.pixelSize: themeManager.fontBodySm
                        font.family: themeManager.fontSans
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    anchors.rightMargin: themeManager.space4
                    text: "Pump-01 监控面板"
                    color: themeManager.textPrimary
                    font.pixelSize: themeManager.fontH3
                    font.family: themeManager.fontSans
                    font.weight: Font.SemiBold
                }
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: topBar.bottom
            anchors.bottom: statusBar.top
            anchors.leftMargin: themeManager.space4
            anchors.rightMargin: themeManager.space4
            color: "transparent"

            Column {
                anchors.fill: parent
                spacing: themeManager.space4

                Row {
                    width: parent.width
                    height: 60
                    spacing: themeManager.space4

                    DeviceControlPanel {
                        id: controlPanel
                        width: 400
                        height: 60
                        isRunning: deviceRunning
                        onStartClicked: handleDeviceStart()
                        onStopClicked: handleDeviceStop()
                        onResetClicked: handleDeviceReset()
                    }
                }

                Row {
                    width: parent.width
                    height: 280
                    spacing: themeManager.space4

                    Column {
                        width: 500
                        height: parent.height
                        spacing: themeManager.space4

                        TrendChart {
                            id: trendChart
                            width: parent.width
                            height: 180
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
                            height: 80
                            spacing: themeManager.space4

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

                    Column {
                        width: parent.width - 520
                        height: parent.height
                        spacing: themeManager.space4

                        Row {
                            width: parent.width
                            height: 120
                            spacing: themeManager.space4

                            DataCard {
                                id: dataCard1
                                label: "温度"
                                value: 25.5
                                unit: "\u00B0C"
                                trend: "up"
                                trendValue: 2.3
                                status: 0
                                decimals: 1
                                width: (parent.width - themeManager.space4 * 3) / 4
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
                                width: (parent.width - themeManager.space4 * 3) / 4
                            }

                            DataCard {
                                id: dataCard3
                                label: "流量"
                                value: 50.3
                                unit: "m\u00B3/h"
                                trend: "stable"
                                status: 1
                                decimals: 1
                                width: (parent.width - themeManager.space4 * 3) / 4
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
                                width: (parent.width - themeManager.space4 * 3) / 4
                            }
                        }

                        ModbusTable {
                            id: modbusTable
                            width: parent.width
                            height: parent.height - 120 - themeManager.space4
                        }
                    }
                }
            }
        }

        Rectangle {
            id: statusBar
            height: 28
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: themeManager.space4
            anchors.rightMargin: themeManager.space4
            anchors.bottomMargin: themeManager.space4
            color: themeManager.bgRaised
            radius: themeManager.radiusMd

            Row {
                anchors.fill: parent
                anchors.leftMargin: themeManager.space4
                anchors.rightMargin: themeManager.space4
                spacing: themeManager.space6

                Row {
                    spacing: themeManager.space2
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        color: themeManager.success500
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "\u2022 已连接"
                        color: themeManager.success500
                        font.pixelSize: themeManager.fontCaption
                        font.family: themeManager.fontSans
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "在线: " + onlineCount + "/" + totalCount
                    color: themeManager.textSecondary
                    font.pixelSize: themeManager.fontCaption
                    font.family: themeManager.fontSans
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "最后更新: " + lastUpdate
                    color: themeManager.textSecondary
                    font.pixelSize: themeManager.fontCaption
                    font.family: themeManager.fontSans
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    text: "v1.0.0"
                    color: themeManager.textTertiary
                    font.pixelSize: themeManager.fontCaption
                    font.family: themeManager.fontSans
                }
            }
        }
    }

    Component.onCompleted: {
        dataTimer.start()
        showToast("success", "系统启动", "工业设备管理系统已成功启动")
    }
}
