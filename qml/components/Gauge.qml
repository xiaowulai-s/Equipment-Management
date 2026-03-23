// 工业设备管理系统 - 仪表盘组件
// Gauge Component - 基于UI设计方案.md

import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    // 属性定义
    property string title: "仪表"
    property real value: 0.0
    property real minValue: 0.0
    property real maxValue: 100.0
    property string unit: "%"
    property int status: 0  // 0: normal, 1: warning, 2: danger
    property int decimals: 0

    // 计算百分比
    property real percentage: (value - minValue) / (maxValue - minValue) * 100

    // 颜色定义
    readonly property color colorSuccess: "#4CAF50"
    readonly property color colorWarning: "#FFC107"
    readonly property color colorError: "#F44336"
    readonly property color colorPrimary: "#2196F3"
    readonly property color colorBgRaised: "#161B22"
    readonly property color colorBorder: "#30363D"
    readonly property color textPrimary: "#E6EDF3"
    readonly property color textSecondary: "#8B949E"
    readonly property color textTertiary: "#6E7681"

    // 状态颜色
    function getStatusColor(status, value, max) {
        var percent = (value / max) * 100
        if (status === 2 || percent >= 90) return colorError
        if (status === 1 || percent >= 75) return colorWarning
        return colorSuccess
    }

    width: 160
    height: 180

    // 仪表盘背景圆
    Rectangle {
        id: gaugeBackground
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -10
        width: 120
        height: 120
        radius: width / 2
        color: colorBgRaised
        border.width: 1
        border.color: colorBorder

        // 外发光效果
        Rectangle {
            anchors.centerIn: parent
            width: parent.width + 16
            height: parent.height + 16
            radius: width / 2
            color: "transparent"
            border.width: 3
            border.color: getStatusColor(status, value, maxValue)
            opacity: 0.2
        }

        // 进度圆弧
        Canvas {
            id: arcCanvas
            anchors.fill: parent
            antialiasing: true

            onPaint: {
                var ctx = getContext("2d")
                var centerX = width / 2
                var centerY = height / 2
                var radius = (width / 2) - 10
                var startAngle = Math.PI * 0.75
                var endAngle = Math.PI * 2.25
                var currentAngle = startAngle + (endAngle - startAngle) * (percentage / 100)

                // 背景弧线
                ctx.clearRect(0, 0, width, height)
                ctx.beginPath()
                ctx.arc(centerX, centerY, radius, startAngle, endAngle)
                ctx.lineWidth = 12
                ctx.strokeStyle = colorBorder
                ctx.lineCap = "round"
                ctx.stroke()

                // 进度弧线 (带渐变)
                if (percentage > 0) {
                    // 创建渐变
                    var gradient = ctx.createLinearGradient(0, 0, width, 0)
                    var statusColor = getStatusColor(status, value, maxValue)
                    gradient.addColorStop(0, colorPrimary)
                    gradient.addColorStop(1, statusColor)

                    ctx.beginPath()
                    ctx.arc(centerX, centerY, radius, startAngle, currentAngle)
                    ctx.lineWidth = 12
                    ctx.strokeStyle = gradient
                    ctx.lineCap = "round"
                    ctx.stroke()
                }

                // 中心数值
                ctx.font = "bold 24px JetBrains Mono, monospace"
                ctx.fillStyle = textPrimary
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                ctx.fillText(value.toFixed(decimals), centerX, centerY - 5)

                // 单位
                ctx.font = "12px Inter, sans-serif"
                ctx.fillStyle = textSecondary
                ctx.fillText(unit, centerX, centerY + 18)
            }
        }

        // 内圈装饰
        Rectangle {
            anchors.centerIn: parent
            width: parent.width - 30
            height: parent.height - 30
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: colorBorder
            opacity: 0.5
        }
    }

    // 刻度标记
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: gaugeBackground.bottom
        anchors.topMargin: 8
        spacing: (root.width - 40) / 4

        Repeater {
            model: 5
            Rectangle {
                width: 2
                height: 4
                radius: 1
                color: textTertiary
            }
        }
    }

    // 范围标签
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: gaugeBackground.bottom
        anchors.topMargin: 20
        spacing: root.width - 80

        Text {
            text: minValue.toFixed(0)
            color: textTertiary
            font.pixelSize: 13
            font.family: "Inter, sans-serif"
        }

        Text {
            text: maxValue.toFixed(0)
            color: textTertiary
            font.pixelSize: 13
            font.family: "Inter, sans-serif"
        }
    }

    // 标题
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 0
        text: title
        color: textPrimary
        font.pixelSize: 14
        font.family: "Inter, sans-serif"
        font.weight: Font.Medium
    }

    // 更新绑定
    onPercentageChanged: arcCanvas.requestPaint()
    onStatusChanged: arcCanvas.requestPaint()
    onValueChanged: arcCanvas.requestPaint()

    Component.onCompleted: arcCanvas.requestPaint()
}