// 工业设备管理系统 - 按钮组件
// Button Component - 基于UI设计方案.md

import QtQuick 2.15

Rectangle {
    id: btn

    property string text: "按钮"
    property string buttonStyleName: "primary"
    property string size: "md"
    property bool enabled: true
    property bool loading: false
    property bool isIconButton: false
    property string iconSource: ""

    signal clicked()

    width: getBtnWidth()
    height: getBtnHeight()
    radius: isIconButton ? 6 : (size === "sm" ? 4 : (size === "lg" ? 8 : 6))
    color: getBtnBgColor()
    border.color: getBtnBorderColor()
    border.width: buttonStyleName === "secondary" ? 1 : 0
    opacity: enabled ? (loading ? 0.7 : 1) : 0.5

    function getBtnWidth() {
        if (isIconButton) return 36
        if (size === "sm") return 80
        if (size === "lg") return 140
        return 100
    }

    function getBtnHeight() {
        if (isIconButton) return 36
        if (size === "sm") return 32
        if (size === "lg") return 44
        return 36
    }

    function getBtnBgColor() {
        if (buttonStyleName === "secondary" || buttonStyleName === "ghost") {
            return isHovered ? "#21262D" : (buttonStyleName === "secondary" ? "#161B22" : "transparent")
        }
        return "transparent"
    }

    function getBtnBorderColor() {
        if (buttonStyleName === "secondary") {
            return isHovered ? "#388BFD" : "#30363D"
        }
        return "transparent"
    }

    function getBtnTextColor() {
        if (!enabled) return "#6E7681"
        if (buttonStyleName === "primary" || buttonStyleName === "danger" || buttonStyleName === "success") {
            return "white"
        }
        if (buttonStyleName === "secondary") return "#E6EDF3"
        return "#8B949E"
    }

    function getBtnGradientStart() {
        if (!isHovered) {
            if (buttonStyleName === "primary") return "#2196F3"
            if (buttonStyleName === "danger") return "#F44336"
            if (buttonStyleName === "success") return "#4CAF50"
        } else {
            if (buttonStyleName === "primary") return "#1E88E5"
            if (buttonStyleName === "danger") return "#E53935"
            if (buttonStyleName === "success") return "#43A047"
        }
        return "#2196F3"
    }

    function getBtnGradientEnd() {
        if (!isHovered) {
            if (buttonStyleName === "primary") return "#1E88E5"
            if (buttonStyleName === "danger") return "#E53935"
            if (buttonStyleName === "success") return "#43A047"
        } else {
            if (buttonStyleName === "primary") return "#1976D2"
            if (buttonStyleName === "danger") return "#D32F2F"
            if (buttonStyleName === "success") return "#388E3C"
        }
        return "#1E88E5"
    }

    function getBtnFontSize() {
        if (size === "sm") return 13
        if (size === "lg") return 16
        return 14
    }

    property bool isHovered: false

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        visible: buttonStyleName === "primary" || buttonStyleName === "danger" || buttonStyleName === "success"
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: btn.getBtnGradientStart() }
            GradientStop { position: 1.0; color: btn.getBtnGradientEnd() }
        }
    }

    Rectangle {
        id: loaderRect
        width: 16
        height: 16
        radius: 8
        color: "transparent"
        border.width: 2
        border.color: btn.enabled ? btn.getBtnTextColor() : "#6E7681"
        visible: btn.loading
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: parent.horizontalCenter

        RotationAnimation on rotation {
            running: btn.loading
            loops: -1
            from: 0
            to: 360
            duration: 600
        }
    }

    Text {
        anchors.centerIn: parent
        text: btn.text
        color: btn.loading ? "transparent" : btn.getBtnTextColor()
        font.pixelSize: btn.getBtnFontSize()
        font.family: "Inter, sans-serif"
        font.weight: 500
        visible: !isIconButton
    }

    MouseArea {
        id: btnHover
        anchors.fill: parent
        cursorShape: btn.enabled ? Qt.PointingHandCursor : Qt.ForbiddenCursor
        hoverEnabled: true
        enabled: btn.enabled && !btn.loading

        onEntered: btn.isHovered = true
        onExited: btn.isHovered = false

        onClicked: {
            if (btn.enabled && !btn.loading) {
                btn.clicked()
            }
        }
    }
}
