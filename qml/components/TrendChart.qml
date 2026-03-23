// 工业设备管理系统 - 趋势图组件
// Trend Chart Component

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // 属性定义
    property string chartTitle: "实时趋势"
    property int timeRange: 6  // 小时
    property var series1Data: []  // 数据系列1
    property var series2Data: []  // 数据系列2
    property var series3Data: []  // 数据系列3
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

    width: 400
    height: 280

    // 图表头
    Rectangle {
        id: chartHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 40
        color: "#161B22"
        radius: 8
        border.width: 1
        border.color: "#30363D"

        Row {
            anchors.fill: parent
            anchors.margins: 12
            layoutDirection: Qt.RightToLeft
            spacing: 8

            // 时间范围按钮
            Repeater {
                model: [
                    { label: "ALL", value: 0 },
                    { label: "24H", value: 24 },
                    { label: "6H", value: 6 },
                    { label: "1H", value: 1 }
                ]

                Rectangle {
                    width: 36
                    height: 24
                    radius: 4
                    color: timeRange === modelData.value ? "#2196F3" : "transparent"
                    border.width: 1
                    border.color: timeRange === modelData.value ? "#2196F3" : "#30363D"

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: timeRange === modelData.value ? "white" : "#8B949E"
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: timeRange = modelData.value
                    }
                }
            }

            // 图表标题
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 16
                text: chartTitle
                color: "#E6EDF3"
                font.pixelSize: 15
                font.family: "Inter, sans-serif"
                font.weight: Font.SemiBold
            }
        }
    }

    // 图表画布
    Rectangle {
        id: chartCanvas
        anchors.top: chartHeader.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: chartLegend.top
        color: "#0F1419"

        Canvas {
            id: trendCanvas
            anchors.fill: parent
            antialiasing: true

            onPaint: {
                var ctx = getContext("2d")
                var w = width
                var h = height
                var paddingLeft = 45
                var paddingRight = 20
                var paddingTop = 15
                var paddingBottom = 30

                var chartWidth = w - paddingLeft - paddingRight
                var chartHeight = h - paddingTop - paddingBottom

                // 清空画布
                ctx.clearRect(0, 0, w, h)

                // 绘制网格线
                ctx.strokeStyle = "#21262D"
                ctx.lineWidth = 1

                // 水平网格线
                for (var i = 0; i <= 4; i++) {
                    var y = paddingTop + (chartHeight / 4) * i
                    ctx.beginPath()
                    ctx.moveTo(paddingLeft, y)
                    ctx.lineTo(w - paddingRight, y)
                    ctx.stroke()

                    // Y轴标签
                    ctx.font = "11px Inter, sans-serif"
                    ctx.fillStyle = "#6E7681"
                    ctx.textAlign = "right"
                    var yLabel = (100 - i * 25).toFixed(0)
                    ctx.fillText(yLabel, paddingLeft - 8, y + 4)
                }

                // 绘制数据系列
                var dataLength = Math.max(series1Data.length, series2Data.length, series3Data.length)
                if (dataLength === 0) return

                var pointSpacing = chartWidth / Math.max(dataLength - 1, 1)

                // 绘制系列1
                drawSeries(ctx, series1Data, series1Max, paddingLeft, paddingTop, chartWidth, chartHeight, series1Color, pointSpacing, true)

                // 绘制系列2
                drawSeries(ctx, series2Data, series2Max, paddingLeft, paddingTop, chartWidth, chartHeight, series2Color, pointSpacing, false)

                // 绘制系列3
                drawSeries(ctx, series3Data, series3Max, paddingLeft, paddingTop, chartWidth, chartHeight, series3Color, pointSpacing, false)
            }

            function drawSeries(ctx, data, maxVal, startX, startY, chartWidth, chartHeight, color, pointSpacing, drawFill) {
                if (data.length === 0) return

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
        id: chartLegend
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 36
        color: "#161B22"
        radius: 8
        border.width: 1
        border.color: "#30363D"

        Row {
            anchors.centerIn: parent
            spacing: 24

            // 系列1
            Row {
                spacing: 8
                Rectangle {
                    width: 12
                    height: 3
                    radius: 1.5
                    color: series1Color
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: series1Name + " (" + series1Unit + ")"
                    color: "#8B949E"
                    font.pixelSize: 13
                    font.family: "Inter, sans-serif"
                }
            }

            // 系列2
            Row {
                spacing: 8
                Rectangle {
                    width: 12
                    height: 3
                    radius: 1.5
                    color: series2Color
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: series2Name + " (" + series2Unit + ")"
                    color: "#8B949E"
                    font.pixelSize: 13
                    font.family: "Inter, sans-serif"
                }
            }

            // 系列3
            Row {
                spacing: 8
                Rectangle {
                    width: 12
                    height: 3
                    radius: 1.5
                    color: series3Color
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    text: series3Name + " (" + series3Unit + ")"
                    color: "#8B949E"
                    font.pixelSize: 13
                    font.family: "Inter, sans-serif"
                }
            }
        }
    }

    // 添加数据点
    function addDataPoint(val1, val2, val3) {
        if (series1Data.length >= maxDataPoints) {
            series1Data.shift()
            series2Data.shift()
            series3Data.shift()
        }

        if (val1 !== undefined) series1Data.push(val1)
        if (val2 !== undefined) series2Data.push(val2)
        if (val3 !== undefined) series3Data.push(val3)

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