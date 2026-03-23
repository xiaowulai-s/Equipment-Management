// 工业设备管理系统 - 数据卡片组件
// Data Card Component - 基于UI设计方案.md

import QtQuick 2.15

Rectangle {
    id: root

    property string label: "温度"
    property real value: 25.5
    property string unit: "°C"
    property string trend: "up"  // up, down, stable
    property real trendValue: 2.3
    property int status: 0  // 0: online, 1: warning, 2: offline
    property int decimals: 1

    width: 200
    height: 140
    radius: 16  // var(--radius-xl)
    color: Qt.rgba(22/255, 27/255, 34/255, 1)  // var(--bg-raised)
    border.color: "#30363D"  // var(--border-default)
    border.width: 1
    clip: true
    gradient: Gradient {
        GradientStop { position: 0.0; color: Qt.rgba(22/255, 27/255, 34/255, 1) }
        GradientStop { position: 1.0; color: Qt.rgba(28/255, 33/255, 40/255, 1) }
    }
    
    // 顶部渐变边框
    Rectangle {
        width: parent.width
        height: 3
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#2196F3" }
            GradientStop { position: 1.0; color: "#00BCD4" }
        }
    }

    // 悬停状态
    property bool isHovered: false

    // 动画状态
    property real hoverOffset: 0

    // 阴影效果
    Rectangle {
        id: shadowRect
        anchors.centerIn: hoverContainer
        anchors.horizontalCenterOffset: 0
        anchors.verticalCenterOffset: 8
        width: root.width
        height: root.height
        radius: root.radius
        color: Qt.rgba(33/255, 150/255, 243/255, 0.16)
        visible: root.isHovered
        z: -1
    }

    // 悬停容器（用于translateY动画）
    Item {
        id: hoverContainer
        anchors.fill: parent
        transform: Translate {
            y: root.hoverOffset
        }
        Behavior on y {
            NumberAnimation {
                duration: 250
                easing.type: Easing.Out
            }
        }

        // 渐变顶部条
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 3
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#2196F3" }
                GradientStop { position: 1.0; color: "#00BCD4" }
            }
        }

        // 状态指示灯
        Rectangle {
            id: statusDot
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 16
            anchors.rightMargin: 16
            width: 10
            height: 10
            radius: 5
            color: getStatusColor()

            // 发光效果
            Rectangle {
                anchors.centerIn: parent
                width: parent.width * 2.5
                height: parent.height * 2.5
                radius: width / 2
                color: "transparent"
                border.width: 1
                border.color: getStatusColor()
                opacity: status === 0 ? 0.4 : (status === 1 ? 0.3 : 0)
            }

            NumberAnimation on opacity {
                running: status !== 2
                loops: -1
                from: 1
                to: 0.5
                duration: 2000
            }
        }

        // 标签文本
        Text {
            id: labelText
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.topMargin: 24
            anchors.leftMargin: 20
            text: label.toUpperCase()
            color: "#8B949E"  // var(--text-secondary)
            font.pixelSize: 13  // var(--text-caption)
            font.family: "Inter, sans-serif"
            font.weight: 500  // var(--font-medium)
            Behavior on color {
                ColorAnimation { duration: 250 }
            }
        }

        // 数值行
        Row {
            id: valueRow
            anchors.top: labelText.bottom
            anchors.left: parent.left
            anchors.topMargin: 8
            anchors.leftMargin: 20
            spacing: 4

            Text {
                id: valueText
                text: value.toFixed(decimals)
                color: "#E6EDF3"  // var(--text-primary)
                font.pixelSize: 32  // var(--text-data)
                font.family: "JetBrains Mono, Consolas, monospace"  // var(--font-mono)
                font.weight: 700  // var(--font-bold)
                lineHeight: 1  // var(--leading-none)
                Behavior on color {
                    ColorAnimation { duration: 250 }
                }
            }

            Text {
                id: unitText
                anchors.verticalCenter: parent.verticalCenter
                text: unit
                color: "#8B949E"  // var(--text-secondary)
                font.pixelSize: 14  // var(--text-body-sm)
                font.family: "Inter, sans-serif"
            }
        }

        // 趋势指示器
        Row {
            id: trendRow
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.bottomMargin: 20
            anchors.leftMargin: 20
            spacing: 6

            // 趋势图标（使用Canvas绘制SVG风格箭头）
            Canvas {
                id: trendIconCanvas
                width: 16
                height: 16
                anchors.verticalCenter: parent.verticalCenter

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.strokeStyle = getTrendColor()
                    ctx.lineWidth = 1.8
                    ctx.lineCap = "round"
                    ctx.lineJoin = "round"

                    if (trend === "up") {
                        ctx.beginPath()
                        ctx.moveTo(4, 8)
                        ctx.lineTo(8, 4)
                        ctx.lineTo(12, 8)
                        ctx.moveTo(8, 4)
                        ctx.lineTo(8, 12)
                        ctx.stroke()
                    } else if (trend === "down") {
                        ctx.beginPath()
                        ctx.moveTo(4, 8)
                        ctx.lineTo(8, 12)
                        ctx.lineTo(12, 8)
                        ctx.moveTo(8, 12)
                        ctx.lineTo(8, 4)
                        ctx.stroke()
                    } else {
                        ctx.beginPath()
                        ctx.moveTo(4, 8)
                        ctx.lineTo(12, 8)
                        ctx.stroke()
                    }
                }
            }

            Text {
                id: trendValueText
                text: trend !== "stable" ? (trend === "up" ? "+" : "-") + trendValue.toFixed(1) + "%" : "稳定"
                color: getTrendColor()
                font.pixelSize: 14  // var(--text-body-sm)
                font.family: "Inter, sans-serif"
                font.weight: 500  // var(--font-medium)
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true

            onEntered: {
                root.isHovered = true
                root.hoverOffset = -4
                root.border.color = "#2196F3"
                labelText.color = "#BBC4CF"
                valueText.color = "#FFFFFF"
            }

            onExited: {
                root.isHovered = false
                root.hoverOffset = 0
                root.border.color = "#30363D"
                labelText.color = "#8B949E"
                valueText.color = "#E6EDF3"
            }
        }
    }

    function getStatusColor() {
        switch (status) {
            case 0: return "#4CAF50"
            case 1: return "#FFC107"
            case 2: return "#F44336"
            default: return "#4CAF50"
        }
    }

    function getTrendColor() {
        if (trend === "up") return "#4CAF50"
        if (trend === "down") return "#F44336"
        return "#8B949E"
    }
}