// 工业设备管理系统 - 设备操作面板组件
// Device Control Panel Component

import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property bool isRunning: false
    property bool isConnected: true
    property bool isLoading: false

    signal startClicked()
    signal stopClicked()
    signal resetClicked()

    function setRunning(running) {
        isRunning = running
    }

    function setLoading(loading) {
        isLoading = loading
    }

    width: 400
    height: 60

    Rectangle {
        anchors.fill: parent
        radius: 8
        color: "#161B22"
        border.width: 1
        border.color: "#30363D"

        Row {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Rectangle {
                id: startButton
                width: 100
                height: 36
                radius: 6
                color: isRunning ? "#30363D" : "#4CAF50"
                border.width: 0

                Text {
                    anchors.centerIn: parent
                    text: isRunning ? "运行中" : "启动"
                    color: isRunning ? "#8B949E" : "white"
                    font.pixelSize: 14
                    font.family: "Inter, sans-serif"
                    font.weight: Font.Medium
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: isRunning ? Qt.ForbiddenCursor : Qt.PointingHandCursor
                    enabled: !isRunning && !isLoading
                    onClicked: {
                        if (!isRunning && !isLoading) {
                            isLoading = true
                            root.startClicked()
                        }
                    }
                }
            }

            Rectangle {
                id: stopButton
                width: 100
                height: 36
                radius: 6
                color: !isRunning ? "#30363D" : "#F44336"
                border.width: 0

                Text {
                    anchors.centerIn: parent
                    text: !isRunning ? "已停止" : "停止"
                    color: !isRunning ? "#8B949E" : "white"
                    font.pixelSize: 14
                    font.family: "Inter, sans-serif"
                    font.weight: Font.Medium
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: !isRunning ? Qt.ForbiddenCursor : Qt.PointingHandCursor
                    enabled: isRunning && !isLoading
                    onClicked: {
                        if (isRunning && !isLoading) {
                            isLoading = true
                            root.stopClicked()
                        }
                    }
                }
            }

            Rectangle {
                id: resetButton
                width: 80
                height: 36
                radius: 6
                color: "#30363D"
                border.width: 1
                border.color: "#388BFD"

                Text {
                    anchors.centerIn: parent
                    text: "复位"
                    color: "#388BFD"
                    font.pixelSize: 14
                    font.family: "Inter, sans-serif"
                    font.weight: Font.Medium
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (!isLoading) {
                            isLoading = true
                            root.resetClicked()
                        }
                    }
                }
            }

            Item {
                width: 1
                height: parent.height
            }

            Rectangle {
                width: 80
                height: 36
                radius: 6
                color: "transparent"
                border.width: 1
                border.color: "#30363D"
                visible: isLoading

                Rectangle {
                    anchors.centerIn: parent
                    width: 16
                    height: 16
                    radius: 8
                    color: "transparent"
                    border.width: 2
                    border.color: "#388BFD"

                    RotationAnimation on rotation {
                        running: isLoading
                        loops: -1
                        from: 0
                        to: 360
                        duration: 600
                    }
                }
            }
        }
    }
}
