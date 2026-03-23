// 工业设备管理系统 - 设备列表组件
// Device List Component

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property int selectedIndex: 0
    property int selectedDeviceIndex: 0

    // 模拟数据模型
    ListModel {
        id: deviceModel

        ListElement {
            groupName: "泵站A区"
        }
        ListElement {
            groupName: "泵站B区"
        }
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
        if (status === 0) return "#4CAF50"  // 在线
        if (status === 1) return "#FFC107"  // 警告
        if (status === 2) return "#F44336"   // 故障/离线
        return "#6E7681"
    }

    // 状态文字
    function getStatusText(status) {
        if (status === 0) return "在线"
        if (status === 1) return "警告"
        if (status === 2) return "离线"
        return "未知"
    }

    // 计算在线设备数
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

    // 计算总设备数
    function getTotalCount() {
        var count = 0
        for (var g = 0; g < deviceGroups.length; g++) {
            count += deviceGroups[g].devices.length
        }
        return count
    }

    width: 260
    height: 400

    // 设备列表容器
    Rectangle {
        anchors.fill: parent
        color: "#0F1419"
        radius: 8
        border.width: 1
        border.color: "#30363D"

        Column {
            anchors.fill: parent

            // 标题栏
            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 48
                color: "#161B22"
                radius: 8

                Row {
                    anchors.fill: parent
                    anchors.margins: 16
                    layoutDirection: Qt.RightToLeft

                    // 在线设备数
                    Rectangle {
                        width: 60
                        height: 24
                        radius: 9999
                        color: "#4CAF50"
                        anchors.verticalCenter: parent.verticalCenter

                        Text {
                            anchors.centerIn: parent
                            text: getOnlineCount() + "/" + getTotalCount() + " 在线"
                            color: "white"
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Medium
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        text: "设备列表"
                        color: "#E6EDF3"
                        font.pixelSize: 15
                        font.family: "Inter, sans-serif"
                        font.weight: Font.SemiBold
                    }
                }
            }

            // 分组列表
            ListView {
                id: deviceListView
                anchors.fill: parent
                anchors.topMargin: 48
                clip: true
                model: deviceGroups.length
                spacing: 8
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

            // 分组标题
            Rectangle {
                id: groupHeader
                width: parent.width
                height: 32
                color: "transparent"
                radius: 6

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    // 展开/折叠图标
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "\u25BC"  // 下箭头
                        color: "#8B949E"
                        font.pixelSize: 10
                        font.family: "Inter, sans-serif"
                        rotation: 0
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: deviceGroups[index].name
                        color: "#8B949E"
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Medium
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "(" + deviceGroups[index].devices.length + ")"
                        color: "#6E7681"
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                }
            }

            // 设备项列表
            Column {
                anchors.leftMargin: 16

                Repeater {
                    model: deviceGroups[index].devices.length

                    Rectangle {
                        id: deviceItem
                        width: parent.width
                        height: 36
                        color: index === root.selectedDeviceIndex && groupName === getCurrentGroup() ?
                               "#42A5F5" + "20" : "transparent"
                        radius: 6
                        border.width: index === root.selectedDeviceIndex && groupName === getCurrentGroup() ? 1 : 0
                        border.color: "#42A5F5"

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

                                // 在线状态发光效果
                                Rectangle {
                                    anchors.centerIn: parent
                                    width: parent.width * 2
                                    height: parent.height * 2
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
                                color: index === root.selectedDeviceIndex && groupName === getCurrentGroup() ?
                                       "#42A5F5" : "#E6EDF3"
                                font.pixelSize: 14
                                font.family: "Inter, sans-serif"
                                font.weight: index === root.selectedDeviceIndex && groupName === getCurrentGroup() ?
                                            Font.Medium : Font.Normal
                            }

                            // IP地址
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.right: parent.right
                                text: deviceData.ip
                                color: "#6E7681"
                                font.pixelSize: 13
                                font.family: "JetBrains Mono, monospace"
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
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