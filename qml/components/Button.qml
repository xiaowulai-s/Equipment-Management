import QtQuick 2.15

Item {
    id: root

    property string text: "按钮"
    property string variant: "primary"
    property string size: "md"
    property bool enabled: true
    property bool loading: false

    signal clicked()

    implicitWidth: getButtonWidth()
    implicitHeight: getButtonHeight()

    function getButtonWidth() {
        if (size === "sm") return 80
        if (size === "lg") return 140
        return 100
    }

    function getButtonHeight() {
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

    Rectangle {
        id: buttonRect
        anchors.fill: parent
        radius: 6
        color: buttonHover.hovered ? getButtonColors().bgHover : getButtonColors().bg
        border.color: buttonHover.hovered ? (variant === "primary" ? "transparent" : "#388BFD") : getButtonColors().border
        border.width: 1
        opacity: root.enabled ? (root.loading ? 0.7 : 1) : 0.5

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: 8

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

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.text
                color: root.loading ? "transparent" : (root.enabled ? getButtonColors().text : "#6E7681"
                font.pixelSize: getFontSize()
                font.family: "Inter, sans-serif"
                font.weight: Font.Medium
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
}
