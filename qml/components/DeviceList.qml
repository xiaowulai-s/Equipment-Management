// 工业设备管理系统 - 设备列表组件
// Device List Component - 基于UI设计方案.md

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property int selectedIndex: 0
    property int selectedDeviceIndex: 0
    property var expandedGroups: [true, true]  // 跟踪每个分组的展开状态

    // 颜色定义
    readonly property color colorSuccess: "#4CAF50"
    readonly property color colorWarning: "#FFC107"
    readonly property color colorError: "#F44336"
    readonly property color colorPrimary: "#2196F3"
    readonly property color colorBgBase: "#0F1419"
    readonly property color colorBgRaised: "#161B22"
    readonly property color colorBgOverlay: "#1C2128"
    readonly property color colorBgHover: "#21262D"
    readonly property color colorBorder: "#30363D"
    readonly property color colorBorderAccent: "#388BFD"
    readonly property color textPrimary: "#E6EDF3"
    readonly property color textSecondary: "#8B949E"
    readonly property color textTertiary: "#6E7681"

    // 模拟数据模型
    ListModel {
        id: deviceModel
        ListElement { groupName: "泵站A区" }
        ListElement { groupName: "泵站B区" }
    }

    // 分组设备数据
    property var deviceGroups: [
        {
            name: "泵站A区",
            devices: [
                { name: "Pump-01", status: 0, ip: "192.168.1.101" },
                { name: "Pump-02", status: 0, ip: "192.168.1.102" },
                { name: "Pump-03", status: 1, ip: "192.168.1.103" }
            ]
        },
        {
            name: "泵站B区",
            devices: [
                { name: "Pump-04", status: 2, ip: "192.168.1.104" },
                { name: "Pump-05", status: 0, ip: "192.168.1.105" }
            ]
        }
    ]

    // 状态颜色
    function getStatusColor(status) {
        if (status === 0) return colorSuccess
        if (status === 1) return colorWarning
        if (status === 2) return colorError
        return textTertiary
    }

    // 状态文字
    function getStatusText(status) {
        if (status === 0) return "在线"
        if (status === 1) return "警告"
        if (status === 2) return "离线"
        return "未知"
    }

    function getOnlineCount() {
        var count = 0
        for (var g = 0; g < deviceGroups.length; g++) {
            var devices = deviceGroups[g].devices
            for (var d = 0; d < devices.length; d++) {
                if (devices[d].status === 0) count++
            }
        }
        return count
    }

    function getTotalCount() {
        var count = 0
        for (var g = 0; g < deviceGroups.length; g++) {
            count += deviceGroups[g].devices.length
        }
        return count
    }

    function getWarningCount() {
        var count = 0
        for (var g = 0; g < deviceGroups.length; g++) {
            var devices = deviceGroups[g].devices
            for (var d = 0; d < devices.length; d++) {
                if (devices[d].status === 1) count++
            }
        }
        return count
    }

    function toggleGroup(index) {
        expandedGroups[index] = !expandedGroups[index]
    }

    width: 260
    height: 400

    // 设备列表容器
    Rectangle {
        anchors.fill: parent
        color: colorBgBase
        radius: 8
        border.width: 1
        border.color: colorBorder

        Column {
            anchors.fill: parent

            // 标题栏
            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 48
                color: colorBgRaised
                radius: 8

                Row {
                    anchors.fill: parent
                    anchors.margins: 16

                    // 标题
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "设备列表"
                        color: textPrimary
                        font.pixelSize: 15
                        font.family: "Inter, sans-serif"
                        font.weight: Font.SemiBold
                    }

                    Item { width: 1; height: 1; anchors.fill: parent }

                    // 在线设备徽章
                    Rectangle {
                        height: 24
                        radius: 12
                        color: Qt.rgba(76/255, 175/255, 80/255, 0.15)
                        border.width: 1
                        border.color: Qt.rgba(76/255, 175/255, 80/255, 0.3)
                        anchors.verticalCenter: parent.verticalCenter

                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                            spacing: 6

                            Rectangle {
                                width: 6
                                height: 6
                                radius: 3
                                color: colorSuccess
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: getOnlineCount() + "/" + getTotalCount()
                                color: colorSuccess
                                font.pixelSize: 12
                                font.family: "Inter, sans-serif"
                                font.weight: Font.Medium
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }

                    // 警告设备徽章（如果存在）
                    Rectangle {
                        height: 24
                        radius: 12
                        color: getWarningCount() > 0 ? Qt.rgba(255/255, 193/255, 7/255, 0.15) : "transparent"
                        border.width: getWarningCount() > 0 ? 1 : 0
                        border.color: Qt.rgba(255/255, 193/255, 7/255, 0.3)
                        anchors.verticalCenter: parent.verticalCenter
                        visible: getWarningCount() > 0

                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                            spacing: 6

                            Rectangle {
                                width: 6
                                height: 6
                                radius: 3
                                color: colorWarning
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: getWarningCount()
                                color: colorWarning
                                font.pixelSize: 12
                                font.family: "Inter, sans-serif"
                                font.weight: Font.Medium
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                }
            }

            // 分组列表
            ListView {
                id: deviceListView
                anchors.top: parent.top
                anchors.topMargin: 48
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                clip: true
                model: deviceGroups.length
                spacing: 4
                delegate: deviceGroupDelegate
            }
        }
    }

    // 设备分组委托
    Component {
        id: deviceGroupDelegate

        Column {
            width: parent ? parent.width - 16 : 0
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 8

            // 分组标题（可点击展开/折叠）
            Rectangle {
                id: groupHeader
                width: parent.width
                height: 32
                color: "transparent"
                radius: 6

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    spacing: 8

                    // 展开/折叠图标（使用Canvas绘制）
                    Canvas {
                        id: expandIcon
                        width: 12
                        height: 12
                        anchors.verticalCenter: parent.verticalCenter

                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)
                            ctx.strokeStyle = textSecondary
                            ctx.lineWidth = 2
                            ctx.lineCap = "round"
                            ctx.lineJoin = "round"

                            var isExpanded = index < expandedGroups.length ? expandedGroups[index] : true

                            if (isExpanded) {
                                // 向上箭头
                                ctx.beginPath()
                                ctx.moveTo(2, 8)
                                ctx.lineTo(6, 4)
                                ctx.lineTo(10, 8)
                                ctx.stroke()
                            } else {
                                // 向下箭头
                                ctx.beginPath()
                                ctx.moveTo(2, 4)
                                ctx.lineTo(6, 8)
                                ctx.lineTo(10, 4)
                                ctx.stroke()
                            }
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: deviceGroups[index].name
                        color: textSecondary
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                        font.weight: Font.SemiBold
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "(" + deviceGroups[index].devices.length + ")"
                        color: textTertiary
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onEntered: groupHeader.color = colorBgHover
                    onExited: groupHeader.color = "transparent"
                    onClicked: {
                        toggleGroup(index)
                        expandIcon.requestPaint()
                    }
                }
            }

            // 设备项列表（根据展开状态显示/隐藏）
            Column {
                anchors.leftMargin: 8
                visible: index < expandedGroups.length ? expandedGroups[index] : true

                Behavior on visible {
                    NumberAnimation {
                        duration: 200
                        easing.type: Easing.Out
                    }
                }

                Repeater {
                    model: deviceGroups[index].devices.length

                    Rectangle {
                        id: deviceItem
                        width: parent.width
                        height: 36
                        color: "transparent"
                        radius: 6

                        // 选中状态边框
                        Rectangle {
                            anchors.fill: parent
                            radius: parent.radius
                            color: "transparent"
                            border.width: 1
                            border.color: "transparent"
                            visible: index === root.selectedDeviceIndex && groupName === getCurrentGroup()
                        }

                        property string groupName: deviceGroups[index].name
                        property var deviceData: deviceGroups[index].devices[modelData]

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            // 状态指示灯
                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: getStatusColor(deviceData.status)
                                anchors.verticalCenter: parent.verticalCenter

                                // 发光效果
                                Rectangle {
                                    anchors.centerIn: parent
                                    width: parent.width * 2.5
                                    height: parent.height * 2.5
                                    radius: width / 2
                                    color: "transparent"
                                    border.width: 1
                                    border.color: getStatusColor(deviceData.status)
                                    opacity: deviceData.status === 0 ? 0.4 : 0
                                }
                            }

                            // 设备名称
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: deviceData.name
                                color: textPrimary
                                font.pixelSize: 14
                                font.family: "Inter, sans-serif"
                                font.weight: index === root.selectedDeviceIndex && groupName === getCurrentGroup() ? Font.Medium : Font.Normal
                            }

                            // IP地址
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.right: parent.right
                                text: deviceData.ip
                                color: textTertiary
                                font.pixelSize: 12
                                font.family: "JetBrains Mono, monospace"
                            }
                        }

                        // 悬停和选中效果
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor

                            onEntered: {
                                parent.color = "#2196F3" + "15"
                            }

                            onExited: {
                                parent.color = "transparent"
                            }

                            onClicked: {
                                root.selectedDeviceIndex = modelData
                                root.selectedIndex = index
                            }
                        }
                    }
                }
            }
        }
    }

    function getCurrentGroup() {
        if (deviceListView.currentItem) {
            return deviceGroups[deviceListView.currentIndex].name
        }
        return ""
    }
}