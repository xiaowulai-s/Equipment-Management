import QtQuick 2.15

Rectangle {
    id: root

    property string label: ""
    property var model: ["选项1", "选项2", "选项3"]
    property int currentIndex: 0
    property bool enabled: true

    signal currentIndexChanged(int index)

    implicitWidth: 200
    implicitHeight: 40
    color: "#161B22"
    border.color: "#30363D"
    border.width: 1
    radius: 8
    clip: true

    property bool isOpen: false

    Row {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 8

        Text {
            id: labelText
            visible: root.label !== ""
            text: root.label + ":"
            color: "#8B949E"
            font.pixelSize: 13
            font.family: "Inter, sans-serif"
        }

        Text {
            id: valueText
            anchors.verticalCenter: parent.verticalCenter
            text: model[currentIndex]
            color: "#E6EDF3"
            font.pixelSize: 14
            font.family: "Inter, sans-serif"
            Layout.fillWidth: true
        }

        Text {
            id: arrowText
            anchors.verticalCenter: parent.verticalCenter
            text: isOpen ? "▲" : "▼"
            color: "#8B949E"
            font.pixelSize: 12
            font.family: "Inter, sans-serif"
        }
    }

    MouseArea {
        id: dropArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        enabled: root.enabled

        onEntered: {
            root.border.color = "#2196F3"
        }

        onExited: {
            root.border.color = "#30363D"
        }

        onClicked: {
            root.isOpen = !root.isOpen
        }
    }

    Rectangle {
        id: dropdown
        anchors.top: parent.bottom
        anchors.topMargin: 4
        anchors.left: parent.left
        anchors.right: parent.right
        height: Math.min(200, (root.model.length * 36) + 16)
        color: "#1C2128"
        border.color: "#30363D"
        border.width: 1
        radius: 8
        visible: root.isOpen
        z: 100
        clip: true

        Column {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 4

            Repeater {
                model: root.model

                Rectangle {
                    width: parent.width
                    height: 36
                    color: mouseArea.containsMouse ? "#21262D" : "transparent"
                    radius: 6

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        text: modelData
                        color: index === root.currentIndex ? "#2196F3" : "#E6EDF3"
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            root.currentIndex = index
                            root.isOpen = false
                            root.currentIndexChanged(index)
                        }
                    }
                }
            }
        }
    }
}
