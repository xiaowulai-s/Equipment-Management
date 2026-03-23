// 工业设备管理系统 - 设备列表组件
// Device List Component - 基于UI设计方案.md

import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property int selectedIndex: 0
    property int selectedDeviceIndex: 0
    property var expandedGroups: [true, true]

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
            if (!deviceGroups[g] || !deviceGroups[g].devices) continue
            var devices = deviceGroups[g].devices
            for (var d = 0; d < devices.length; d++) {
                if (devices[d] && devices[d].status === 0) count++
            }
        }
        return count
    }

    function getTotalCount() {
        var count = 0
        for (var g = 0; g < deviceGroups.length; g++) {
            if (!deviceGroups[g] || !deviceGroups[g].devices) continue
            count += deviceGroups[g].devices.length
        }
        return count
    }

    function getWarningCount() {
        var count = 0
        for (var g = 0; g < deviceGroups.length; g++) {
            if (!deviceGroups[g] || !deviceGroups[g].devices) continue
            var devices = deviceGroups[g].devices
            for (var d = 0; d < devices.length; d++) {
                if (devices[d] && devices[d].status === 1) count++
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

        // 标题栏
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 48
            color: colorBgRaised
            radius: 8

            Text {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                text: "设备列表"
                color: textPrimary
                font.pixelSize: 15
                font.family: "Inter, sans-serif"
                font.weight: 600
            }

            // 在线设备徽章
            Rectangle {
                anchors.right: warningBadge.visible ? warningBadge.left : parent.right
                anchors.rightMargin: warningBadge.visible ? 8 : 16
                anchors.verticalCenter: parent.verticalCenter
                height: 24
                radius: 12
                color: Qt.rgba(76/255, 175/255, 80/255, 0.15)
                border.width: 1
                border.color: Qt.rgba(76/255, 175/255, 80/255, 0.3)

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

            // 警告设备徽章
            Rectangle {
                id: warningBadge
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                height: 24
                radius: 12
                color: Qt.rgba(255/255, 193/255, 7/255, 0.15)
                border.width: 1
                border.color: Qt.rgba(255/255, 193/255, 7/255, 0.3)
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

    // 设备分组委托
    Component {
        id: deviceGroupDelegate

        Column {
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 8

            // 分组标题（可点击展开/折叠）
            Rectangle {
                id: groupHeader
                width: parent ? parent.width : 0
                height: 32
                color: "transparent"
                radius: 6

                // 展开/折叠图标
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: expandedGroups[index] ? "\u25BC" : "\u25B6"
                    color: textSecondary
                    font.pixelSize: 10
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 28
                    anchors.verticalCenter: parent.verticalCenter
                    text: deviceGroups[index] ? deviceGroups[index].name : ""
                    color: textSecondary
                    font.pixelSize: 13
                    font.family: "Inter, sans-serif"
                    font.weight: 600
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 28 + (deviceGroups[index] ? deviceGroups[index].name.length * 13 + 10 : 60)
                    anchors.verticalCenter: parent.verticalCenter
                    text: "(" + (deviceGroups[index] && deviceGroups[index].devices ? deviceGroups[index].devices.length : 0) + ")"
                    color: textTertiary
                    font.pixelSize: 13
                    font.family: "Inter, sans-serif"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onEntered: groupHeader.color = colorBgHover
                    onExited: groupHeader.color = "transparent"
                    onClicked: toggleGroup(index)
                }
            }

            // 设备项列表
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
                    model: deviceGroups[index] && deviceGroups[index].devices ? deviceGroups[index].devices.length : 0

                    Rectangle {
                        id: deviceItem
                        width: parent ? parent.width : 0
                        height: 36
                        color: "transparent"
                        radius: 6

                        property var deviceData: deviceGroups[index] && deviceGroups[index].devices && deviceGroups[index].devices[modelData] ? deviceGroups[index].devices[modelData] : ({name: "", status: 0, ip: ""})

                        // 状态指示灯
                        Rectangle {
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            width: 8
                            height: 8
                            radius: 4
                            color: getStatusColor(deviceData.status)
                        }

                        // 设备名称
                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 28
                            anchors.verticalCenter: parent.verticalCenter
                            text: deviceData.name
                            color: textPrimary
                            font.pixelSize: 14
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Normal
                        }

                        // IP地址
                        Text {
                            anchors.right: parent.right
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            text: deviceData.ip
                            color: textTertiary
                            font.pixelSize: 12
                            font.family: "JetBrains Mono, monospace"
                        }

                        // 悬停和选中效果
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor

                            onEntered: {
                                parent.color = "#2196F315"
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
            return deviceGroups[deviceListView.currentIndex] ? deviceGroups[deviceListView.currentIndex].name : ""
        }
        return ""
    }
}
