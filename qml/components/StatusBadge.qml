import QtQuick 2.15

Item {
    id: root

    property string text: "正常"
    property string type: "success"
    property bool showDot: true
    property bool animateDot: true

    implicitWidth: text ? badgeText.width + (showDot ? 30 : 20) : 36
    implicitHeight: 24

    function getBadgeColors() {
        switch (type) {
            case "success": return { bg: "#4CAF50", bgAlpha: "#4CAF5026", border: "#4CAF504D", text: "#4CAF50" }
            case "warning": return { bg: "#FFC107", bgAlpha: "#FFC10726", border: "#FFC1074D", text: "#FFC107" }
            case "error": return { bg: "#F44336", bgAlpha: "#F4433626", border: "#F443364D", text: "#F44336" }
            case "info": return { bg: "#2196F3", bgAlpha: "#2196F326", border: "#2196F34D", text: "#2196F3" }
            case "neutral": return { bg: "#30363D", bgAlpha: "#1C2128", border: "#30363D", text: "#8B949E" }
            default: return { bg: "#4CAF50", bgAlpha: "#4CAF5026", border: "#4CAF504D", text: "#4CAF50" }
        }
    }

    Rectangle {
        id: badgeRect
        anchors.fill: parent
        radius: 4
        color: getBadgeColors().bgAlpha
        border.width: 1
        border.color: getBadgeColors().border

        Row {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: showDot ? 8 : 10
            spacing: 4

            Rectangle {
                id: dotRect
                width: 6
                height: 6
                radius: 3
                color: getBadgeColors().text
                visible: root.showDot

                NumberAnimation on opacity {
                    running: root.animateDot && root.showDot
                    loops: -1
                    from: 1
                    to: 0.5
                    duration: 1500
                }
            }

            Text {
                id: badgeText
                anchors.verticalCenter: parent.verticalCenter
                text: root.text
                color: getBadgeColors().text
                font.pixelSize: 13
                font.family: "Inter, sans-serif"
                font.weight: Font.Medium
                textTransform: Text.Uppercase
                letterSpacing: 0.8
            }
        }
    }
}
