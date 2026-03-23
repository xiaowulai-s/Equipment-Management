import QtQuick 2.15

Rectangle {
    id: root

    property string label: ""
    property string placeholder: "请输入..."
    property string text: ""
    property bool enabled: true
    property bool readOnly: false

    signal textChanged(string text)

    implicitWidth: 280
    implicitHeight: 56
    color: "#161B22"
    border.color: "#30363D"
    border.width: 1
    radius: 8
    clip: true

    Rectangle {
        id: focusHighlight
        anchors.fill: parent
        anchors.margins: -1
        color: "transparent"
        border.color: inputItem.focus ? "#2196F3" : "transparent"
        border.width: 2
        radius: root.radius
        visible: !root.readOnly
    }

    Text {
        id: labelText
        visible: root.label !== ""
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.top: parent.top
        anchors.topMargin: 8
        text: root.label
        color: "#8B949E"
        font.pixelSize: 12
        font.family: "Inter, sans-serif"
        font.weight: Font.Medium
    }

    TextInput {
        id: inputItem
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: labelText.visible ? labelText.bottom : parent.top
        anchors.topMargin: labelText.visible ? 4 : 16
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        anchors.bottom: parent.bottom
        anchors.bottomMargin: labelText.visible ? 8 : 16
        text: root.text
        placeholderText: root.placeholder
        color: "#E6EDF3"
        selectionColor: "#2196F3"
        selectedTextColor: "white"
        font.pixelSize: labelText.visible ? 14 : 16
        font.family: "Inter, sans-serif"
        enabled: root.enabled && !root.readOnly
        verticalAlignment: TextInput.AlignVCenter

        onTextChanged: {
            root.text = text
            root.textChanged(text)
        }
    }

    Rectangle {
        id: readOnlyOverlay
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.2)
        visible: root.readOnly || !root.enabled
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.enabled && !root.readOnly
        onClicked: {
            inputItem.forceActiveFocus()
        }
    }
}
