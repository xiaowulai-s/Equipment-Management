// 工业设备管理系统 - 趋势图组件
// Trend Chart Component - 基于UI设计方案.md

import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    // 属性定义
    property string chartTitle: "实时趋势"
    property int timeRange: 6  // 小时
    property var series1Data: []
    property var series2Data: []
    property var series3Data: []
    property string series1Name: "温度"
    property string series2Name: "压力"
    property string series3Name: "流量"
    property string series1Unit: "\u00B0C"
    property string series2Unit: "MPa"
    property string series3Unit: "m\u00B3/h"
    property color series1Color: "#2196F3"
    property color series2Color: "#00BCD4"
    property color series3Color: "#4CAF50"
    property real series1Max: 100
    property real series2Max: 10
    property real series3Max: 200

    // 内部状态
    property int maxDataPoints: 60
    property int currentTimeIndex: 0

    // 颜色定义
    readonly property color colorBgBase: "#0F1419"
    readonly property color colorBgRaised: "#161B22"
    readonly property color colorPrimary: "#2196F3"
    readonly property color colorBorder: "#30363D"
    readonly property color colorBorderMuted: "#21262D"
    readonly property color textPrimary: "#E6EDF3"
    readonly property color textSecondary: "#8B949E"
    readonly property color textTertiary: "#6E7681"

    width: 400
    height: 280

    // 图表容器
    Rectangle {
        anchors.fill: parent
        color: colorBgBase
        radius: 8
        border.width: 1
        border.color: colorBorder

        // 图表头
        Rectangle {
            id: chartHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 48
            color: colorBgRaised
            radius: 8

            Text {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                text: chartTitle
                color: textPrimary
                font.pixelSize: 15
                font.family: "Inter, sans-serif"
                font.weight: 600
            }

            // 时间范围按钮
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                // 1H 按钮
                Rectangle {
                    width: 44
                    height: 28
                    radius: 6
                    color: timeRange === 1 ? colorPrimary : "transparent"
                    border.width: 1
                    border.color: timeRange === 1 ? colorPrimary : colorBorder

                    Text {
                        anchors.centerIn: parent
                        text: "1H"
                        color: timeRange === 1 ? "white" : textSecondary
                        font.pixelSize: 12
                        font.family: "Inter, sans-serif"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: timeRange = 1
                    }
                }

                // 6H 按钮
                Rectangle {
                    width: 44
                    height: 28
                    radius: 6
                    color: timeRange === 6 ? colorPrimary : "transparent"
                    border.width: 1
                    border.color: timeRange === 6 ? colorPrimary : colorBorder

                    Text {
                        anchors.centerIn: parent
                        text: "6H"
                        color: timeRange === 6 ? "white" : textSecondary
                        font.pixelSize: 12
                        font.family: "Inter, sans-serif"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: timeRange = 6
                    }
                }

                // 24H 按钮
                Rectangle {
                    width: 52
                    height: 28
                    radius: 6
                    color: timeRange === 24 ? colorPrimary : "transparent"
                    border.width: 1
                    border.color: timeRange === 24 ? colorPrimary : colorBorder

                    Text {
                        anchors.centerIn: parent
                        text: "24H"
                        color: timeRange === 24 ? "white" : textSecondary
                        font.pixelSize: 12
                        font.family: "Inter, sans-serif"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: timeRange = 24
                    }
                }

                // ALL 按钮
                Rectangle {
                    width: 44
                    height: 28
                    radius: 6
                    color: timeRange === 0 ? colorPrimary : "transparent"
                    border.width: 1
                    border.color: timeRange === 0 ? colorPrimary : colorBorder

                    Text {
                        anchors.centerIn: parent
                        text: "ALL"
                        color: timeRange === 0 ? "white" : textSecondary
                        font.pixelSize: 12
                        font.family: "Inter, sans-serif"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: timeRange = 0
                    }
                }
            }
        }

        // 图表画布
        Rectangle {
            anchors.top: chartHeader.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: legendRect.top
            anchors.leftMargin: 48
            anchors.rightMargin: 16
            anchors.bottomMargin: 8
            color: "transparent"

            Canvas {
                id: trendCanvas
                anchors.fill: parent
                antialiasing: true

                onPaint: {
                    var ctx = getContext("2d")
                    var w = width
                    var h = height
                    var paddingTop = 10
                    var paddingBottom = 25

                    var chartHeight = h - paddingTop - paddingBottom

                    // 清空画布
                    ctx.clearRect(0, 0, w, h)

                    // 绘制网格线
                    ctx.strokeStyle = colorBorderMuted
                    ctx.lineWidth = 1

                    // 水平网格线
                    for (var i = 0; i <= 4; i++) {
                        var y = paddingTop + (chartHeight / 4) * i
                        ctx.beginPath()
                        ctx.moveTo(0, y)
                        ctx.lineTo(w, y)
                        ctx.stroke()

                        // Y轴标签
                        ctx.font = "11px Inter, sans-serif"
                        ctx.fillStyle = textTertiary
                        ctx.textAlign = "right"
                        var yLabel = (100 - i * 25).toFixed(0)
                        ctx.fillText(yLabel, -8, y + 4)
                    }

                    // 绘制数据系列
                    var dataLength = Math.max(series1Data.length, series2Data.length, series3Data.length)
                    if (dataLength === 0) return

                    var chartWidth = w
                    var pointSpacing = chartWidth / Math.max(dataLength - 1, 1)

                    // 绘制系列1 (带填充)
                    drawSeries(ctx, series1Data, series1Max, 0, paddingTop, chartWidth, chartHeight, series1Color, pointSpacing, true)

                    // 绘制系列2
                    drawSeries(ctx, series2Data, series2Max, 0, paddingTop, chartWidth, chartHeight, series2Color, pointSpacing, false)

                    // 绘制系列3
                    drawSeries(ctx, series3Data, series3Max, 0, paddingTop, chartWidth, chartHeight, series3Color, pointSpacing, false)
                }

                function drawSeries(ctx, data, maxVal, startX, startY, chartWidth, chartHeight, color, pointSpacing, drawFill) {
                    if (!data || data.length === 0) return

                    ctx.beginPath()
                    ctx.strokeStyle = color
                    ctx.lineWidth = 2

                    var points = []
                    for (var i = 0; i < data.length; i++) {
                        var x = startX + i * pointSpacing
                        var y = startY + chartHeight * (1 - data[i] / maxVal)
                        points.push({x: x, y: y})

                        if (i === 0) {
                            ctx.moveTo(x, y)
                        } else {
                            ctx.lineTo(x, y)
                        }
                    }
                    ctx.stroke()

                    // 绘制填充区域
                    if (drawFill && points.length > 0) {
                        ctx.lineTo(points[points.length - 1].x, startY + chartHeight)
                        ctx.lineTo(points[0].x, startY + chartHeight)
                        ctx.closePath()
                        ctx.fillStyle = color
                        ctx.globalAlpha = 0.1
                        ctx.fill()
                        ctx.globalAlpha = 1.0
                    }

                    // 绘制数据点
                    for (var j = 0; j < points.length; j++) {
                        ctx.beginPath()
                        ctx.arc(points[j].x, points[j].y, 3, 0, Math.PI * 2)
                        ctx.fillStyle = color
                        ctx.fill()
                    }
                }
            }
        }

        // 图例
        Rectangle {
            id: legendRect
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 48
            color: colorBgRaised
            radius: 8

            Row {
                anchors.centerIn: parent
                spacing: 32

                // 系列1
                Row {
                    spacing: 8
                    Rectangle {
                        width: 16
                        height: 4
                        radius: 2
                        color: series1Color
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: series1Name + " (" + series1Unit + ")"
                        color: textSecondary
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                // 系列2
                Row {
                    spacing: 8
                    Rectangle {
                        width: 16
                        height: 4
                        radius: 2
                        color: series2Color
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: series2Name + " (" + series2Unit + ")"
                        color: textSecondary
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                // 系列3
                Row {
                    spacing: 8
                    Rectangle {
                        width: 16
                        height: 4
                        radius: 2
                        color: series3Color
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: series3Name + " (" + series3Unit + ")"
                        color: textSecondary
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }

    // 添加数据点
    function addDataPoint(val1, val2, val3) {
        if (typeof val1 === 'number' && !isNaN(val1)) {
            if (series1Data.length >= maxDataPoints) {
                series1Data.shift()
            }
            series1Data.push(val1)
        }
        if (typeof val2 === 'number' && !isNaN(val2)) {
            if (series2Data.length >= maxDataPoints) {
                series2Data.shift()
            }
            series2Data.push(val2)
        }
        if (typeof val3 === 'number' && !isNaN(val3)) {
            if (series3Data.length >= maxDataPoints) {
                series3Data.shift()
            }
            series3Data.push(val3)
        }

        trendCanvas.requestPaint()
    }

    // 清除数据
    function clearData() {
        series1Data = []
        series2Data = []
        series3Data = []
        trendCanvas.requestPaint()
    }
}
