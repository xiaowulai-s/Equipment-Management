import QtQuick 2.15

Item {
    id: root

    property string label: ""
    property bool checked: false
    property bool enabled: true

    signal toggled(bool checked)

    implicitWidth: 200
    implicitHeight: 24

    Rectangle {
        id: checkBox
        width: 20
        height: 20
        radius: 4
        color: root.checked ? "#2196F3" : "#161B22"
        border.color: root.checked ? "#2196F3" : "#30363D"
        border.width: 2
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        Behavior on color {
            NumberAnimation { duration: 150 }
        }
        Behavior on border.color {
            NumberAnimation { duration: 150 }
        }
    }

    Text {
        id: checkMark
        anchors.centerIn: checkBox
        text: "✓"
        color: "white"
        font.pixelSize: 14
        font.family: "Inter, sans-serif"
        font.weight: Font.Bold
        visible: root.checked
    }

    Text {
        id: labelText
        visible: root.label !== ""
        anchors.left: checkBox.right
        anchors.leftMargin: 10
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
