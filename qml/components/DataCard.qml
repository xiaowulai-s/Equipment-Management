import QtQuick 2.15

Rectangle {
    id: root

    property string label: "温度"
    property real value: 25.5
    property string unit: "°C"
    property string trend: "up"
    property real trendValue: 2.3
    property int status: 0
    property int decimals: 1

    width: 200
    height: 140
    radius: 12
    color: "#161B22"
    border.color: "#30363D"
    border.width: 1
    clip: true

    function getStatusColor() {
        switch (status) {
            case 0: return "#4CAF50"
            case 1: return "#FFC107"
            case 2: return "#F44336"
            default: return "#4CAF50"
        }
    }

    function getTrendColor() {
        if (trend === "up") return "#4CAF50"
        if (trend === "down") return "#F44336"
        return "#8B949E"
    }

    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 3
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#2196F3" }
            GradientStop { position: 1.0; color: "#00BCD4" }
        }
    }

    Rectangle {
        id: statusDot
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 16
        anchors.rightMargin: 16
        width: 10
        height: 10
        radius: 5
        color: getStatusColor()

        NumberAnimation on opacity {
            running: status !== 2
            loops: -1
            from: 1
            to: 0.5
            duration: 2000
        }
    }

    Text {
        id: labelText
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.topMargin: 24
        anchors.leftMargin: 20
        text: label.toUpperCase()
        color: "#8B949E"
        font.pixelSize: 13
        font.family: "Inter, sans-serif"
        font.weight: Font.Medium
    }

    Row {
        id: valueRow
        anchors.top: labelText.bottom
        anchors.left: parent.left
        anchors.topMargin: 8
        anchors.leftMargin: 20
        spacing: 4

        Text {
            id: valueText
            text: value.toFixed(decimals)
            color: "#E6EDF3"
            font.pixelSize: 24
            font.family: "JetBrains Mono, Consolas, monospace"
            font.weight: Font.Bold
        }

        Text {
            id: unitText
            anchors.verticalCenter: parent.verticalCenter
            text: unit
            color: "#8B949E"
            font.pixelSize: 14
            font.family: "Inter, sans-serif"
        }
    }

    Row {
        id: trendRow
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.bottomMargin: 20
        anchors.leftMargin: 20
        spacing: 4

        Text {
            id: trendIcon
            text: trend === "up" ? "▲" : (trend === "down" ? "▼" : "–")
            color: getTrendColor()
            font.pixelSize: 12
            font.family: "Inter, sans-serif"
        }

        Text {
            id: trendValueText
            text: trend !== "stable" ? trendValue.toFixed(1) + "%" : "稳定"
            color: getTrendColor()
            font.pixelSize: 13
            font.family: "Inter, sans-serif"
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true

        onEntered: {
            root.border.color = "#2196F3"
        }

        onExited: {
            root.border.color = "#30363D"
        }
    }
}
