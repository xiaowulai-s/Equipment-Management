import QtQuick 2.15

Item {
    id: root

    property int toastDuration: 3000
    property int maxToasts: 5

    signal toastShown(string message, string type)

    function showToast(message, type) {
        var toast = toastComponent.createObject(toastContainer, {
            "message": message,
            "type": type
        });
        toast.show();
    }

    function success(message) {
        showToast(message, "success");
    }

    function error(message) {
        showToast(message, "error");
    }

    function warning(message) {
        showToast(message, "warning");
    }

    function info(message) {
        showToast(message, "info");
    }

    Component {
        id: toastComponent

        Rectangle {
            id: toastItem
            property string message: ""
            property string type: "info"

            width: 360
            height: 64
            radius: 12
            color: "#1C2128"
            border.color: getToastBorder()
            border.width: 1
            opacity: 0

            function getToastIcon() {
                switch (type) {
                    case "success": return "✓"
                    case "error": return "✕"
                    case "warning": return "!"
                    case "info": return "i"
                    default: return "i"
                }
            }

            function getToastColor() {
                switch (type) {
                    case "success": return "#4CAF50"
                    case "error": return "#F44336"
                    case "warning": return "#FFC107"
                    case "info": return "#2196F3"
                    default: return "#2196F3"
                }
            }

            function getToastBorder() {
                switch (type) {
                    case "success": return "#4CAF504D"
                    case "error": return "#F443364D"
                    case "warning": return "#FFC1074D"
                    case "info": return "#2196F34D"
                    default: return "#2196F34D"
                }
            }

            function show() {
                slideIn.running = true;
                removeTimer.start();
            }

            function remove() {
                slideOut.running = true;
            }

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.top: parent.top
                anchors.topMargin: 16
                spacing: 12

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    color: getToastColor() + "26"

                    Text {
                        anchors.centerIn: parent
                        text: getToastIcon()
                        color: getToastColor()
                        font.pixelSize: 16
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                    }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: toastItem.message
                    color: "#E6EDF3"
                    font.pixelSize: 14
                    font.family: "Inter, sans-serif"
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    width: 280
                }

                Rectangle {
                    id: closeBtn
                    width: 28
                    height: 28
                    radius: 14
                    color: "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: "#8B949E"
                        font.pixelSize: 20
                        font.family: "Inter, sans-serif"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onEntered: closeBtn.color = "#21262D"
                        onExited: closeBtn.color = "transparent"
                        onClicked: toastItem.remove()
                    }
                }
            }

            Timer {
                id: removeTimer
                interval: root.toastDuration
                onTriggered: toastItem.remove()
            }

            NumberAnimation {
                id: slideIn
                target: toastItem
                property: "opacity"
                from: 0
                to: 1
                duration: 200
                easing.type: Easing.OutQuad
            }

            NumberAnimation {
                id: slideOut
                target: toastItem
                property: "opacity"
                from: 1
                to: 0
                duration: 200
                easing.type: Easing.InQuad
                onFinished: toastItem.destroy()
            }
        }
    }

    Item {
        id: toastContainer
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: 20
        z: 9999
        clip: true
    }
}
