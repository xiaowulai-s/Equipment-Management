// 工业设备管理系统 - 模态对话框组件
// Modal Dialog Component

import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property string title: "对话框"
    property string message: ""
    property bool modal: true
    property int dialogWidth: 400
    property int dialogHeight: 200

    signal accepted()
    signal rejected()
    signal closed()

    function open() {
        dialog.visible = true
    }

    function close() {
        dialog.visible = false
        closed()
    }

    function accept() {
        accepted()
        close()
    }

    function reject() {
        rejected()
        close()
    }

    Rectangle {
        id: dialog
        visible: false
        anchors.centerIn: parent
        width: dialogWidth
        height: dialogHeight
        z: 1000

        Rectangle {
            anchors.fill: parent
            color: "#1C2128"
            radius: 12
            border.width: 1
            border.color: "#30363D"

            Column {
                anchors.fill: parent

                Rectangle {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 48
                    color: "#161B22"
                    radius: 12

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 16
                        spacing: 8

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: title
                            color: "#E6EDF3"
                            font.pixelSize: 16
                            font.family: "Inter, sans-serif"
                            font.weight: Font.SemiBold
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            width: 32
                            height: 32
                            radius: 6
                            color: "transparent"
                            anchors.verticalCenter: parent.verticalCenter

                            Text {
                                anchors.centerIn: parent
                                text: "\u2716"
                                color: "#8B949E"
                                font.pixelSize: 16
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: reject()
                            }
                        }
                    }
                }

                Rectangle {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 1
                    color: "#30363D"
                }

                Rectangle {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: dialogHeight - 48 - 56
                    anchors.topMargin: 48
                    color: "transparent"

                    Text {
                        anchors.fill: parent
                        anchors.margins: 16
                        text: message
                        color: "#8B949E"
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        wrapMode: Text.WordWrap
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 56
                    color: "#161B22"
                    radius: 12

                    Row {
                        anchors.fill: parent
                        anchors.rightMargin: 16
                        layoutDirection: Qt.RightToLeft
                        spacing: 12

                        Rectangle {
                            width: 80
                            height: 36
                            radius: 6
                            color: "#4CAF50"

                            Text {
                                anchors.centerIn: parent
                                text: "确定"
                                color: "white"
                                font.pixelSize: 14
                                font.family: "Inter, sans-serif"
                                font.weight: Font.Medium
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: accept()
                            }
                        }

                        Rectangle {
                            width: 80
                            height: 36
                            radius: 6
                            color: "#30363D"
                            border.width: 1
                            border.color: "#388BFD"

                            Text {
                                anchors.centerIn: parent
                                text: "取消"
                                color: "#388BFD"
                                font.pixelSize: 14
                                font.family: "Inter, sans-serif"
                                font.weight: Font.Medium
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: reject()
                            }
                        }
                    }
                }
            }

            NumberAnimation {
                id: fadeIn
                target: dialog
                property: "opacity"
                from: 0
                to: 1
                duration: 250
            }

            NumberAnimation {
                id: fadeOut
                target: dialog
                property: "opacity"
                from: 1
                to: 0
                duration: 250
            }

            function show() {
                fadeIn.running = true
            }

            function hide() {
                fadeOut.running = true
            }

            onVisibleChanged: {
                if (visible) {
                    show()
                }
            }
        }

        Rectangle {
            id: overlay
            anchors.fill: parent
            color: "rgba(0, 0, 0, 0.6)"
            z: 999

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    if (modal) {
                        reject()
                    }
                }
            }

            visible: dialog.visible

            NumberAnimation {
                id: overlayFadeIn
                target: overlay
                property: "opacity"
                from: 0
                to: 1
                duration: 250
            }

            NumberAnimation {
                id: overlayFadeOut
                target: overlay
                property: "opacity"
                from: 1
                to: 0
                duration: 250
            }

            onVisibleChanged: {
                if (visible) {
                    overlayFadeIn.running = true
                }
            }
        }
    }
}
