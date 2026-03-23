// 工业设备管理系统 - Toast通知组件
// Toast Notification Component

import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property int toastDuration: 3000
    property int maxToasts: 5

    function show(type, title, message) {
        toastModel.append({
            toastType: type,
            toastTitle: title,
            toastMessage: message,
            toastId: Date.now()
        })

        if (toastModel.count > maxToasts) {
            toastModel.remove(0)
        }
    }

    function success(title, message) {
        show("success", title, message)
    }

    function error(title, message) {
        show("error", title, message)
    }

    function warning(title, message) {
        show("warning", title, message)
    }

    function info(title, message) {
        show("info", title, message)
    }

    ListModel {
        id: toastModel
    }

    ListView {
        anchors.top: parent.top
        anchors.right: parent.right
        width: 350
        height: childrenRect.height
        spacing: 8
        model: toastModel
        verticalLayoutDirection: ListView.BottomToTop

        delegate: toastDelegate
    }

    Component {
        id: toastDelegate

        Rectangle {
            id: toastItem
            width: 350
            height: 80
            radius: 8
            border.width: 1
            property string toastType: "info"

            function getTypeColor(type) {
                if (type === "success") return "#4CAF50"
                if (type === "error") return "#F44336"
                if (type === "warning") return "#FFC107"
                return "#2196F3"
            }

            function getIcon(type) {
                if (type === "success") return "\u2714"
                if (type === "error") return "\u2716"
                if (type === "warning") return "!"
                return "i"
            }

            color: "#1C2128"
            border.color: getTypeColor(toastType)

            Row {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                Rectangle {
                    width: 36
                    height: 36
                    radius: 18
                    color: getTypeColor(toastType) + "20"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: getIcon(toastType)
                        color: getTypeColor(toastType)
                        font.pixelSize: 16
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4

                    Text {
                        text: toastTitle
                        color: "#E6EDF3"
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.SemiBold
                    }

                    Text {
                        text: toastMessage
                        color: "#8B949E"
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                    }
                }
            }

            NumberAnimation {
                id: slideIn
                target: toastItem
                property: "opacity"
                from: 0
                to: 1
                duration: 250
                easing.type: Easing.Out
            }

            NumberAnimation {
                id: slideOut
                target: toastItem
                property: "opacity"
                from: 1
                to: 0
                duration: 250
                easing.type: Easing.In
            }

            Timer {
                id: removeTimer
                interval: toastDuration
                onTriggered: {
                    slideOut.running = true
                    slideOut.completed.connect(function() {
                        toastModel.remove(index)
                    })
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    removeTimer.triggered("")
                    removeTimer.running = true
                }
            }

            Component.onCompleted: {
                slideIn.running = true
                removeTimer.start()
            }
        }
    }
}
