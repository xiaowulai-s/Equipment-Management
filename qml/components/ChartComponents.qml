// 工业设备管理系统 - 趋势图表组件

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: trendChartLibrary
    color: Theme.bgBase
    
    // ============== 趋势折线图 ==============
    Component {
        id: trendChartComponent
        
        Rectangle {
            id: chartContainer
            property string title: "趋势图"
            property var dataPoints: []  // [{x: 0, y: 50}, {x: 1, y: 60}, ...]
            property string theme: "light"  // light, dark
            property real minValue: 0
            property real maxValue: 100
            property int maxPoints: 60
            
            color: chartContainer.theme === "dark" ? Theme.bgRaised : Theme.bgBase
            border {
                color: Theme.borderDefault
                width: 1
            }
            radius: 8
            clip: true
            
            Column {
                anchors { fill: parent; margins: 16 }
                spacing: 16
                
                // 图表标题
                Text {
                    text: chartContainer.title
                    color: Theme.textPrimary
                    font.pixelSize: 16
                    font.weight: Font.Medium
                }
                
                // 画布绘制区域
                Rectangle {
                    width: parent.width
                    height: 200
                    color: chartContainer.theme === "dark" ? Theme.bgBase : Theme.bgRaised
                    radius: 6
                    
                    Canvas {
                        id: canvas
                        anchors.fill: parent
                        
                        onPaint: {
                            var ctx = getContext("2d")
                            var w = width
                            var h = height
                            var padding = 30
                            var graphWidth = w - padding * 2
                            var graphHeight = h - padding * 2
                            
                            // 清空画布
                            ctx.clearRect(0, 0, w, h)
                            
                            // 设置样式
                            ctx.strokeStyle = Theme.borderDefault
                            ctx.fillStyle = "transparent"
                            ctx.lineWidth = 1
                            
                            // 绘制网格线
                            for (var i = 0; i <= 4; i++) {
                                var y = padding + (graphHeight / 4) * i
                                ctx.beginPath()
                                ctx.moveTo(padding, y)
                                ctx.lineTo(w - padding, y)
                                ctx.stroke()
                            }
                            
                            // 绘制Y轴标签
                            ctx.fillStyle = Theme.textTertiary
                            ctx.font = "12px Inter"
                            ctx.textAlign = "right"
                            for (var i = 0; i <= 4; i++) {
                                var value = chartContainer.maxValue - (chartContainer.maxValue - chartContainer.minValue) * (i / 4)
                                var y = padding + (graphHeight / 4) * i
                                ctx.fillText(Math.round(value), padding - 5, y + 4)
                            }
                            
                            // 绘制趋势线
                            if (chartContainer.dataPoints.length > 1) {
                                ctx.strokeStyle = Theme.accent500
                                ctx.lineWidth = 2
                                ctx.lineJoin = "round"
                                ctx.beginPath()
                                
                                for (var i = 0; i < chartContainer.dataPoints.length; i++) {
                                    var point = chartContainer.dataPoints[i]
                                    var range = chartContainer.maxValue - chartContainer.minValue
                                    var normalizedY = (chartContainer.maxValue - point.y) / range
                                    
                                    var x = padding + (graphWidth / (chartContainer.dataPoints.length - 1 || 1)) * i
                                    var y = padding + graphHeight * normalizedY
                                    
                                    if (i === 0) {
                                        ctx.moveTo(x, y)
                                    } else {
                                        ctx.lineTo(x, y)
                                    }
                                }
                                ctx.stroke()
                                
                                // 绘制渐变背景
                                var gradient = ctx.createLinearGradient(0, padding, 0, h - padding)
                                gradient.addColorStop(0, chartContainer.theme === "dark" ? 
                                    "rgba(33, 150, 243, 0.2)" : "rgba(33, 150, 243, 0.1)")
                                gradient.addColorStop(1, "rgba(33, 150, 243, 0)")
                                
                                ctx.strokeStyle = Theme.accent500
                                ctx.lineWidth = 0
                                ctx.fillStyle = gradient
                                ctx.beginPath()
                                
                                for (var i = 0; i < chartContainer.dataPoints.length; i++) {
                                    var point = chartContainer.dataPoints[i]
                                    var range = chartContainer.maxValue - chartContainer.minValue
                                    var normalizedY = (chartContainer.maxValue - point.y) / range
                                    
                                    var x = padding + (graphWidth / (chartContainer.dataPoints.length - 1 || 1)) * i
                                    var y = padding + graphHeight * normalizedY
                                    
                                    if (i === 0) {
                                        ctx.moveTo(x, y)
                                    } else {
                                        ctx.lineTo(x, y)
                                    }
                                }
                                
                                ctx.lineTo(w - padding, h - padding)
                                ctx.lineTo(padding, h - padding)
                                ctx.closePath()
                                ctx.fill()
                            }
                            
                            // 绘制数据点
                            ctx.fillStyle = Theme.accent500
                            for (var i = 0; i < chartContainer.dataPoints.length; i++) {
                                var point = chartContainer.dataPoints[i]
                                var range = chartContainer.maxValue - chartContainer.minValue
                                var normalizedY = (chartContainer.maxValue - point.y) / range
                                
                                var x = padding + (graphWidth / (chartContainer.dataPoints.length - 1 || 1)) * i
                                var y = padding + graphHeight * normalizedY
                                
                                ctx.beginPath()
                                ctx.arc(x, y, 3, 0, Math.PI * 2)
                                ctx.fill()
                            }
                        }
                        
                        Connections {
                            target: chartContainer
                            onDataPointsChanged: canvas.requestPaint()
                        }
                    }
                }
                
                // 底部统计信息
                Row {
                    width: parent.width
                    spacing: 16
                    
                    Column {
                        spacing: 4
                        
                        Text {
                            text: "最大值"
                            color: Theme.textTertiary
                            font.pixelSize: 12
                        }
                        
                        Text {
                            text: chartContainer.dataPoints.length > 0 ? 
                                Math.max.apply(null, chartContainer.dataPoints.map(p => p.y)).toFixed(1) : 
                                "--"
                            color: Theme.textPrimary
                            font.pixelSize: 16
                            font.weight: Font.Bold
                        }
                    }
                    
                    Column {
                        spacing: 4
                        
                        Text {
                            text: "最小值"
                            color: Theme.textTertiary
                            font.pixelSize: 12
                        }
                        
                        Text {
                            text: chartContainer.dataPoints.length > 0 ? 
                                Math.min.apply(null, chartContainer.dataPoints.map(p => p.y)).toFixed(1) : 
                                "--"
                            color: Theme.textPrimary
                            font.pixelSize: 16
                            font.weight: Font.Bold
                        }
                    }
                    
                    Column {
                        spacing: 4
                        
                        Text {
                            text: "平均值"
                            color: Theme.textTertiary
                            font.pixelSize: 12
                        }
                        
                        Text {
                            text: chartContainer.dataPoints.length > 0 ? 
                                (chartContainer.dataPoints.reduce((a, b) => ({y: a.y + b.y})).y / chartContainer.dataPoints.length).toFixed(1) : 
                                "--"
                            color: Theme.textPrimary
                            font.pixelSize: 16
                            font.weight: Font.Bold
                        }
                    }
                    
                    Item {
                        Layout.fillWidth: true
                    }
                }
            }
            
            function addDataPoint(value) {
                var newData = chartContainer.dataPoints.slice()
                newData.push({x: newData.length, y: value})
                
                if (newData.length > chartContainer.maxPoints) {
                    newData = newData.slice(-chartContainer.maxPoints)
                }
                
                // 重新索引x值
                newData.forEach((p, i) => { p.x = i })
                chartContainer.dataPoints = newData
            }
            
            function clearData() {
                chartContainer.dataPoints = []
            }
        }
    }
    
    // ============== 柱状图 ==============
    Component {
        id: barChartComponent
        
        Rectangle {
            id: barContainer
            property string title: "统计图"
            property var data: []  // [{label: "A", value: 50}, ...]
            property real maxValue: 100
            
            color: Theme.bgBase
            border {
                color: Theme.borderDefault
                width: 1
            }
            radius: 8
            clip: true
            
            Column {
                anchors { fill: parent; margins: 16 }
                spacing: 16
                
                Text {
                    text: barContainer.title
                    color: Theme.textPrimary
                    font.pixelSize: 16
                    font.weight: Font.Medium
                }
                
                Rectangle {
                    width: parent.width
                    height: 200
                    color: Theme.bgRaised
                    radius: 6
                    
                    Canvas {
                        anchors.fill: parent
                        
                        onPaint: {
                            var ctx = getContext("2d")
                            var w = width
                            var h = height
                            var padding = 30
                            var data = barContainer.data || []
                            
                            if (data.length === 0) return
                            
                            var barWidth = (w - padding * 2) / data.length
                            
                            data.forEach((item, index) => {
                                var barHeight = (item.value / barContainer.maxValue) * (h - padding * 2)
                                var x = padding + index * barWidth + barWidth * 0.1
                                var y = h - padding - barHeight
                                
                                ctx.fillStyle = Theme.accent500
                                ctx.fillRect(x, y, barWidth * 0.8, barHeight)
                                
                                ctx.fillStyle = Theme.textTertiary
                                ctx.font = "12px Inter"
                                ctx.textAlign = "center"
                                ctx.fillText(item.label, x + barWidth * 0.4, h - padding + 15)
                            })
                        }
                        
                        Connections {
                            target: barContainer
                            onDataChanged: canvas.requestPaint()
                        }
                    }
                }
            }
        }
    }
}
