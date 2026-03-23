// 工业设备管理系统 - 数据卡片组件
// Data Card Component

import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    // 属性定义
    property string label: "数据标签"
    property real value: 0.0
    property string unit: ""
    property string trend: "stable"  // up, down, stable
    property real trendValue: 0.0
    property int status: 0  // 0: normal, 1: warning, 2: error
    property int decimals: 1  // 数值小数位数

    // 颜色常量
    readonly property color colorSuccess: "#4CAF50"
    readonly property color colorWarning: "#FFC107"
    readonly property color colorError: "#F44336"
    readonly property color colorPrimary: "#2196F3"
    readonly property color colorAccent: "#00BCD4"
    readonly property color colorBgRaised: "#161B22"
    readonly property color colorBgOverlay: "#1C2128"
    readonly property color colorBorder: "#30363D"
    readonly property color colorTextPrimary: "#E6EDF3"
    readonly property color colorTextSecondary: "#8B949E"

    // 状态颜色
    function getStatusColor(status) {
        if (status === 1) return colorWarning
        if (status === 2) return colorError
        return colorSuccess
    }

    // 趋势箭头和颜色
    function getTrendInfo(trend) {
        if (trend === "up")
            return { icon: "\u2191", color: colorSuccess }
        if (trend === "down")
            return { icon: "\u2193", color: colorError }
        return { icon: "\u2192", color: colorTextSecondary }
    }

    width: 200
    height: 120

    // 卡片主体
    Rectangle {
        id: cardBackground
        anchors.fill: parent
        radius: 12
        color: colorBgRaised
        border.color: colorBorder

        // 顶部渐变装饰条
        Rectangle {
            id: topBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 3
            radius: 12
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: colorPrimary }
                GradientStop { position: 1.0; color: colorAccent }
            }
        }

        // 状态指示灯
        Rectangle {
            id: statusIndicator
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 16
            width: 10
            height: 10
            radius: 5
            color: getStatusColor(status)

            // 发光效果
            Rectangle {
                anchors.centerIn: parent
                width: parent.width * 2
                height: parent.height * 2
                radius: width / 2
                color: "transparent"
                border.width: 2
                border.color: getStatusColor(status)
                opacity: 0.3
            }
        }

        Column {
            anchors.left: parent.left
            anchors.leftMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            // 标签
            Text {
                text: label
                color: colorTextSecondary
                font.pixelSize: 13
                font.family: "Inter, sans-serif"
                font.weight: Font.Medium
                textFormat: Text.PlainText
            }

            // 数值
            Row {
                spacing: 4
                Text {
                    id: valueText
                    text: value.toFixed(decimals)
                    color: colorTextPrimary
                    font.pixelSize: 24
                    font.family: "JetBrains Mono, monospace"
                    font.weight: Font.Bold
                    textFormat: Text.PlainText
                }

                Text {
                    text: unit
                    color: colorTextSecondary
                    font.pixelSize: 15
                    font.family: "Inter, sans-serif"
                    anchors.verticalCenter: valueText.verticalCenter
                    textFormat: Text.PlainText
                }
            }

            // 趋势指示
            Row {
                spacing: 4
                id: trendRow

                Text {
                    text: getTrendInfo(trend).icon
                    color: getTrendInfo(trend).color
                    font.pixelSize: 14
                    font.family: "Inter, sans-serif"
                    textFormat: Text.PlainText
                }

                Text {
                    text: (trend !== "stable" ? (trend === "up" ? "+" : "-") : "") +
                          (trend !== "stable" ? trendValue.toFixed(1) + "%" : "稳定")
                    color: getTrendInfo(trend).color
                    font.pixelSize: 14
                    font.family: "Inter, sans-serif"
                    textFormat: Text.PlainText
                }
            }
        }

        // 悬停效果
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor

            onEntered: {
                cardBackground.color = colorBgOverlay
                cardBackground.border.color = colorPrimary
            }

            onExited: {
                cardBackground.color = colorBgRaised
                cardBackground.border.color = colorBorder
            }
        }
    }
}