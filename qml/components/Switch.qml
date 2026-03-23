import QtQuick 2.15

Item {
    id: root

    property string label: ""
    property bool checked: false
    property bool enabled: true

    signal toggled(bool checked)

    implicitWidth: 140
    implicitHeight: 32

    Rectangle {
        id: switchBg
        width: 52
        height: 28
        radius: 14
        color: root.checked ? "#2196F3" : "#30363D"
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        Behavior on color {
            NumberAnimation { duration: 200 }
        }
    }

    Rectangle {
        id: switchHandle
        width: 24
        height: 24
        radius: 12
        color: "white"
        x: root.checked ? 26 : 2
        y: 4
        Behavior on x {
            NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
        }
    }

    Text {
        id: labelText
        visible: root.label !== ""
        anchors.left: switchBg.right
        anchors.leftMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        color: root.enabled ? "#E6EDF3" : "#6E7681"
        font.pixelSize: 14
        font.family: "Inter, sans-serif"
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ForbiddenCursor
        enabled: root.enabled
        onClicked: {
            root.checked = !root.checked
            root.toggled(root.checked)
        }
    }
}
