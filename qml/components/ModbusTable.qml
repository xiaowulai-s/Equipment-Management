// 工业设备管理系统 - Modbus表格组件
// Modbus Table Component

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // 颜色常量
    readonly property color colorSuccess: "#4CAF50"
    readonly property color colorWarning: "#FFC107"
    readonly property color colorError: "#F44336"
    readonly property color colorPrimary: "#2196F3"
    readonly property color colorPrimaryLight: "#42A5F5"
    readonly property color colorBgBase: "#0F1419"
    readonly property color colorBgRaised: "#161B22"
    readonly property color colorBgOverlay: "#1C2128"
    readonly property color colorBorder: "#30363D"
    readonly property color colorBorderMuted: "#21262D"
    readonly property color colorTextPrimary: "#E6EDF3"
    readonly property color colorTextSecondary: "#8B949E"

    // 属性
    property int currentPage: 1
    property int pageSize: 5

    // 数据模型
    property var tableData: [
        { address: "0x0001", functionCode: "03", variableName: "温度传感器", value: "25.5", unit: "\u00B0C", status: 0, statusText: "正常" },
        { address: "0x0002", functionCode: "03", variableName: "压力变送器", value: "1.23", unit: "MPa", status: 0, statusText: "正常" },
        { address: "0x0003", functionCode: "03", variableName: "流量计", value: "50.3", unit: "m\u00B3/h", status: 1, statusText: "预警" },
        { address: "0x0004", functionCode: "03", variableName: "功率表", value: "15.2", unit: "kW", status: 2, statusText: "故障" },
        { address: "0x0005", functionCode: "03", variableName: "频率", value: "50.0", unit: "Hz", status: 0, statusText: "正常" },
        { address: "0x0006", functionCode: "03", variableName: "效率", value: "95.2", unit: "%", status: 0, statusText: "正常" },
        { address: "0x0007", functionCode: "03", variableName: "入口压力", value: "0.85", unit: "MPa", status: 0, statusText: "正常" },
        { address: "0x0008", functionCode: "03", variableName: "出口压力", value: "1.23", unit: "MPa", status: 0, statusText: "正常" }
    ]

    property int totalRows: tableData.length
    property int totalPages: Math.max(1, Math.ceil(totalRows / pageSize))

    // 状态颜色
    function getStatusColor(status) {
        if (status === 0) return colorSuccess
        if (status === 1) return colorWarning
        if (status === 2) return colorError
        return colorTextSecondary
    }

    width: 500
    height: 320

    // 表格容器
    Rectangle {
        anchors.fill: parent
        color: colorBgBase
        radius: 8
        border.width: 1
        border.color: colorBorder

        Column {
            anchors.fill: parent

            // 表头
            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 40
                color: colorBgRaised
                radius: 8

                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 8

                    // 地址列
                    Rectangle {
                        width: 70
                        height: parent.height
                        color: "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "地址"
                            color: colorTextSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Medium
                        }
                    }

                    // 功能码列
                    Rectangle {
                        width: 60
                        height: parent.height
                        color: "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "功能码"
                            color: colorTextSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Medium
                        }
                    }

                    // 变量名列
                    Rectangle {
                        width: 120
                        height: parent.height
                        color: "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "变量名"
                            color: colorTextSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Medium
                        }
                    }

                    // 数值列
                    Rectangle {
                        width: 80
                        height: parent.height
                        color: "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "数值"
                            color: colorTextSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Medium
                        }
                    }

                    // 状态列
                    Rectangle {
                        width: 80
                        height: parent.height
                        color: "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "状态"
                            color: colorTextSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Medium
                        }
                    }
                }
            }

            // 表格数据区
            Rectangle {
                anchors.top: parent.top
                anchors.topMargin: 40
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 44
                color: "transparent"
                clip: true

                ListView {
                    id: tableView
                    anchors.fill: parent
                    model: tableData
                    clip: true
                    delegate: tableRowDelegate
                    spacing: 0
                }
            }

            // 分页栏
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 44
                color: colorBgRaised
                radius: 8

                Row {
                    anchors.fill: parent
                    anchors.margins: 12
                    layoutDirection: Qt.RightToLeft
                    spacing: 12

                    // 分页信息
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "第 " + currentPage + " / " + totalPages + " 页"
                        color: colorTextSecondary
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                    }

                    // 分页按钮
                    Row {
                        spacing: 4

                        // 上一页
                        Rectangle {
                            width: 28
                            height: 28
                            radius: 4
                            color: currentPage > 1 ? colorBgRaised : colorBgOverlay
                            border.width: 1
                            border.color: colorBorder

                            Text {
                                anchors.centerIn: parent
                                text: "\u276E"
                                color: currentPage > 1 ? colorTextPrimary : colorTextSecondary
                                font.pixelSize: 12
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: currentPage > 1 ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: if (currentPage > 1) currentPage--
                            }
                        }

                        // 下一页
                        Rectangle {
                            width: 28
                            height: 28
                            radius: 4
                            color: currentPage < totalPages ? colorBgRaised : colorBgOverlay
                            border.width: 1
                            border.color: colorBorder

                            Text {
                                anchors.centerIn: parent
                                text: "\u276F"
                                color: currentPage < totalPages ? colorTextPrimary : colorTextSecondary
                                font.pixelSize: 12
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: currentPage < totalPages ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: if (currentPage < totalPages) currentPage++
                            }
                        }
                    }

                    // 总行数
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "共 " + totalRows + " 条"
                        color: colorTextSecondary
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                    }
                }
            }
        }
    }

    // 表格行委托
    Component {
        id: tableRowDelegate

        Rectangle {
            width: parent ? parent.width : 0
            height: 44
            color: index % 2 === 0 ? colorBgBase : colorBgOverlay

            // 底部边框线
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: colorBorderMuted
            }

            Row {
                anchors.fill: parent
                anchors.leftMargin: 8

                // 地址列
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 70
                    text: modelData.address
                    color: colorPrimaryLight
                    font.pixelSize: 14
                    font.family: "JetBrains Mono, monospace"
                    font.weight: Font.Medium
                }

                // 功能码列
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 60
                    text: modelData.functionCode
                    color: colorTextPrimary
                    font.pixelSize: 14
                    font.family: "JetBrains Mono, monospace"
                }

                // 变量名列
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 120
                    text: modelData.variableName
                    color: colorTextPrimary
                    font.pixelSize: 14
                    font.family: "Inter, sans-serif"
                }

                // 数值列
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 80
                    spacing: 2

                    Text {
                        text: modelData.value
                        color: colorTextPrimary
                        font.pixelSize: 14
                        font.family: "JetBrains Mono, monospace"
                        font.weight: Font.Medium
                    }

                    Text {
                        text: modelData.unit
                        color: colorTextSecondary
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                // 状态列
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 80
                    spacing: 8

                    // 状态指示点
                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        color: getStatusColor(modelData.status)
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: modelData.statusText
                        color: getStatusColor(modelData.status)
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Medium
                    }
                }
            }

            // 悬停效果
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onEntered: {
                    parent.color = "#42A5F5" + "20"
                }

                onExited: {
                    parent.color = index % 2 === 0 ? colorBgBase : colorBgOverlay
                }
            }
        }
    }
}