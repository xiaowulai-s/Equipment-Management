// 工业设备管理系统 - 按钮组件
// Button Component - 基于UI设计方案.md

import QtQuick 2.15

Item {
    id: root

    property string text: "按钮"
    property string variant: "primary"  // primary, secondary, ghost, danger, success
    property string size: "md"  // sm, md, lg
    property bool enabled: true
    property bool loading: false
    property bool isIconButton: false
    property string iconSource: ""

    signal clicked()

    implicitWidth: getButtonWidth()
    implicitHeight: getButtonHeight()

    function getButtonWidth() {
        if (isIconButton) return 36
        if (size === "sm") return 80
        if (size === "lg") return 140
        return 100
    }

    function getButtonHeight() {
        if (isIconButton) return 36
        if (size === "sm") return 32
        if (size === "lg") return 44
        return 36
    }

    function getButtonColors() {
        switch (variant) {
            case "primary": return { bg: "#2196F3", bgHover: "#1E88E5", text: "white", border: "transparent" }
            case "secondary": return { bg: "#161B22", bgHover: "#21262D", text: "#E6EDF3", border: "#30363D" }
            case "ghost": return { bg: "transparent", bgHover: "#21262D", text: "#8B949E", border: "transparent" }
            case "danger": return { bg: "#F44336", bgHover: "#E53935", text: "white", border: "transparent" }
            case "success": return { bg: "#4CAF50", bgHover: "#43A047", text: "white", border: "transparent" }
            default: return { bg: "#2196F3", bgHover: "#1E88E5", text: "white", border: "transparent" }
        }
    }

    function getFontSize() {
        if (size === "sm") return 13
        if (size === "lg") return 16
        return 14
    }

    // 按钮主矩形
    Rectangle {
        id: buttonRect
        anchors.fill: parent
        radius: isIconButton ? 6 : (size === "sm" ? 4 : (size === "lg" ? 8 : 6))
        color: buttonHover.hovered ? getButtonColors().bgHover : getButtonColors().bg
        border.color: buttonHover.hovered ? (variant === "primary" ? "transparent" : "#388BFD") : getButtonColors().border
        border.width: 1
        opacity: root.enabled ? (root.loading ? 0.7 : 1) : 0.5

        // 悬停时的阴影效果
        Rectangle {
            id: shadowOverlay
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.width: 0
            visible: buttonHover.hovered && root.enabled

            Rectangle {
                anchors.centerIn: parent
                anchors.horizontalCenterOffset: 0
                anchors.verticalCenterOffset: 2
                width: parent.width
                height: parent.height
                radius: parent.radius
                color: Qt.rgba(0, 0, 0, 0.15)
                z: -1
            }
        }

        // 主按钮渐变
        Rectangle {
            id: gradientBg
            anchors.fill: parent
            radius: parent.radius
            visible: variant === "primary" || variant === "danger" || variant === "success"
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: buttonHover.hovered ?
                        (variant === "primary" ? "#1E88E5" :
                         variant === "danger" ? "#E53935" : "#43A047") :
                        (variant === "primary" ? "#2196F3" :
                         variant === "danger" ? "#F44336" : "#4CAF50")
                }
                GradientStop {
                    position: 1.0
                    color: buttonHover.hovered ?
                        (variant === "primary" ? "#1976D2" :
                         variant === "danger" ? "#D32F2F" : "#388E3C") :
                        (variant === "primary" ? "#1E88E5" :
                         variant === "danger" ? "#E53935" : "#43A047")
                }
            }
        }

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: 8

            // 加载指示器
            Rectangle {
                id: loaderRect
                width: 16
                height: 16
                radius: 8
                color: "transparent"
                border.width: 2
                border.color: root.enabled ? getButtonColors().text : "#6E7681"
                visible: root.loading
                anchors.verticalCenter: parent.verticalCenter

                RotationAnimation on rotation {
                    running: root.loading
                    loops: -1
                    from: 0
                    to: 360
                    duration: 600
                }
            }

            // 图标（使用SVG路径模拟）
            Rectangle {
                id: iconPlaceholder
                width: 18
                height: 18
                color: "transparent"
                visible: isIconButton && iconSource !== ""
                anchors.verticalCenter: parent.verticalCenter

                // SVG风格图标
                Canvas {
                    id: iconCanvas
                    anchors.fill: parent
                    visible: parent.visible

                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        ctx.strokeStyle = root.enabled ? getButtonColors().text : "#6E7681"
                        ctx.lineWidth = 2
                        ctx.lineCap = "round"
                        ctx.lineJoin = "round"

                        // 根据iconSource绘制不同图标
                        if (iconSource === "add") {
                            ctx.beginPath()
                            ctx.moveTo(9, 3)
                            ctx.lineTo(9, 15)
                            ctx.stroke()
                            ctx.beginPath()
                            ctx.moveTo(3, 9)
                            ctx.lineTo(15, 9)
                            ctx.stroke()
                        } else if (iconSource === "edit") {
                            ctx.beginPath()
                            ctx.moveTo(11, 2)
                            ctx.lineTo(15, 6)
                            ctx.lineTo(6, 15)
                            ctx.lineTo(2, 15)
                            ctx.lineTo(2, 11)
                            ctx.closePath()
                            ctx.stroke()
                        } else if (iconSource === "delete") {
                            ctx.beginPath()
                            ctx.moveTo(3, 6)
                            ctx.lineTo(15, 6)
                            ctx.moveTo(6, 6)
                            ctx.lineTo(6, 15)
                            ctx.lineTo(10, 15)
                            ctx.lineTo(10, 6)
                            ctx.stroke()
                            ctx.beginPath()
                            ctx.moveTo(2, 6)
                            ctx.lineTo(16, 6)
                            ctx.stroke()
                        } else if (iconSource === "settings") {
                            ctx.beginPath()
                            ctx.arc(9, 9, 3, 0, Math.PI * 2)
                            ctx.stroke()
                            ctx.beginPath()
                            ctx.moveTo(9, 2)
                            ctx.lineTo(9, 4)
                            ctx.moveTo(9, 14)
                            ctx.lineTo(9, 16)
                            ctx.moveTo(2, 9)
                            ctx.lineTo(4, 9)
                            ctx.moveTo(14, 9)
                            ctx.lineTo(16, 9)
                            ctx.moveTo(4, 4)
                            ctx.lineTo(5.5, 5.5)
                            ctx.moveTo(12.5, 12.5)
                            ctx.lineTo(14, 14)
                            ctx.moveTo(4, 14)
                            ctx.lineTo(5.5, 12.5)
                            ctx.moveTo(12.5, 5.5)
                            ctx.lineTo(14, 4)
                            ctx.stroke()
                        } else if (iconSource === "chart") {
                            ctx.beginPath()
                            ctx.moveTo(2, 15)
                            ctx.lineTo(2, 8)
                            ctx.lineTo(6, 12)
                            ctx.lineTo(10, 5)
                            ctx.lineTo(14, 10)
                            ctx.lineTo(17, 7)
                            ctx.stroke()
                        }
                    }
                }
            }

            // 文本（图标按钮时隐藏）
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.text
                color: root.loading ? "transparent" : (root.enabled ? getButtonColors().text : "#6E7681")
                font.pixelSize: getFontSize()
                font.family: "Inter, sans-serif"
                font.weight: Font.Medium
                visible: !isIconButton
            }
        }

        MouseArea {
            id: buttonHover
            anchors.fill: parent
            cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ForbiddenCursor
            hoverEnabled: true
            enabled: root.enabled && !root.loading

            onClicked: {
                if (root.enabled && !root.loading) {
                    root.clicked()
                }
            }
        }
    }

    // 聚焦指示器
    Rectangle {
        anchors.fill: parent
        radius: parent ? buttonRect.radius : 6
        color: "transparent"
        border.width: 2
        border.color: Qt.rgba(33/255, 150/255, 243/255, 0.5)
        visible: false  // 通过focus_policy控制
    }
}