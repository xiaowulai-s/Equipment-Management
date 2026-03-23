// 工业设备管理系统 - 按钮组件
// Button Component

import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    // 属性定义
    property string text: "Button"
    property string type: "primary"  // primary, secondary, ghost, danger, success
    property bool disabled: false
    property bool loading: false
    property int fontSize: 14
    property int paddingH: 16
    property int paddingV: 8
    property alias icon: iconLoader.source

    signal clicked()

    // 颜色常量
    readonly property color colorPrimary: "#2196F3"
    readonly property color colorPrimaryDark: "#1E88E5"
    readonly property color colorSuccess: "#4CAF50"
    readonly property color colorSuccessDark: "#43A047"
    readonly property color colorError: "#F44336"
    readonly property color colorErrorDark: "#E53935"
    readonly property color colorBgRaised: "#161B22"
    readonly property color colorBgOverlay: "#1C2128"
    readonly property color colorBgHover: "#21262D"
    readonly property color colorBgActive: "#30363D"
    readonly property color colorBorder: "#30363D"
    readonly property color colorBorderAccent: "#388BFD"
    readonly property color colorTextPrimary: "#E6EDF3"
    readonly property color colorTextTertiary: "#6E7681"

    width: buttonLoader.width
    height: buttonLoader.height

    // 按钮背景颜色
    function getBackgroundColor(type, hovered, pressed, disabled) {
        if (disabled) return colorBgOverlay

        switch(type) {
            case "primary":
                if (pressed) return "#1976D2"
                if (hovered) return colorPrimaryDark
                return colorPrimary
            case "secondary":
                if (pressed) return colorBgActive
                if (hovered) return colorBgHover
                return colorBgRaised
            case "ghost":
                if (pressed) return colorBgActive
                if (hovered) return colorBgHover
                return "transparent"
            case "danger":
                if (pressed) return colorErrorDark
                if (hovered) return colorErrorDark
                return colorError
            case "success":
                if (pressed) return colorSuccessDark
                if (hovered) return colorSuccessDark
                return colorSuccess
            default:
                return colorPrimary
        }
    }

    // 按钮边框颜色
    function getBorderColor(type, hovered, disabled) {
        if (disabled) return colorBorder

        switch(type) {
            case "secondary":
                if (hovered) return colorBorderAccent
                return colorBorder
            default:
                return "transparent"
        }
    }

    // 按钮文本颜色
    function getTextColor(type, disabled) {
        if (disabled) return colorTextTertiary

        switch(type) {
            case "primary":
            case "danger":
            case "success":
                return "white"
            case "secondary":
            case "ghost":
                return colorTextPrimary
            default:
                return "white"
        }
    }

    // 动态样式加载器
    Loader {
        id: buttonLoader
        anchors.centerIn: parent

        sourceComponent: Rectangle {
            width: buttonText.width + root.paddingH * 2 + (iconLoader.source !== "" ? iconLoader.width + 4 : 0)
            height: buttonText.height + root.paddingV * 2
            radius: 6
            color: getBackgroundColor(root.type, mouseArea.containsMouse, mouseArea.pressed, root.disabled)
            border.color: getBorderColor(root.type, mouseArea.containsMouse, root.disabled)
            Behavior on color {
                ColorAnimation { duration: 150 }
            }
            Behavior on border.color {
                ColorAnimation { duration: 150 }
            }

            Row {
                anchors.centerIn: parent
                spacing: 4

                Image {
                    id: iconLoader
                    width: source !== "" ? 16 : 0
                    height: source !== "" ? 16 : 0
                    anchors.verticalCenter: parent.verticalCenter
                    visible: source !== ""
                }

                Text {
                    id: buttonText
                    text: root.text
                    color: getTextColor(root.type, root.disabled)
                    font.pixelSize: root.fontSize
                    font.family: "Inter, sans-serif"
                    font.weight: Font.Medium
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            // 加载指示器
            Loader {
                id: loadingLoader
                anchors.centerIn: parent
                visible: root.loading
                sourceComponent: Rectangle {
                    width: 16
                    height: 16
                    radius: 8
                    color: "transparent"
                    border.width: 2
                    border.color: parent.parent.color
                    RotationAnimation on rotation {
                        running: root.loading
                        loops: -1
                        from: 0
                        to: 360
                        duration: 600
                    }
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: root.disabled ? Qt.ForbiddenCursor : Qt.PointingHandCursor
                onClicked: {
                    if (!root.disabled && !root.loading) {
                        root.clicked()
                    }
                }
            }
        }
    }

    MouseArea {
        anchors.fill: buttonLoader
        enabled: false
    }
}