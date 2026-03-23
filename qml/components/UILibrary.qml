// 工业设备管理系统 - 完整组件库
// 对应 UI设计预览.html 的所有UI元素

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: componentLibrary
    color: Theme.bgBase
    
    // ============== 色彩系统演示 ==============
    
    // 按钮组件库
    Component {
        id: buttonComponent
        
        Rectangle {
            id: button
            property string text: "按钮"
            property string variant: "primary"  // primary, secondary, ghost, danger, success
            property string size: "md"          // sm, md, lg
            property bool enabled: true
            property bool loading: false
            
            signal clicked()
            
            implicitWidth: {
                if (size === "sm") return 76
                if (size === "lg") return 128
                return 100
            }
            implicitHeight: {
                if (size === "sm") return 32
                if (size === "lg") return 40
                return 36
            }
            
            radius: size === "sm" ? 4 : (size === "lg" ? 8 : 6)
            
            color: {
                if (!enabled) return Theme.bgActive
                if (mouseArea.containsMouse) return getHoverColor()
                return getColor()
            }
            
            border.color: variant === "secondary" ? Theme.borderDefault : "transparent"
            border.width: variant === "secondary" ? 1 : 0
            
            function getColor() {
                switch (variant) {
                    case "primary": return Theme.primary500
                    case "secondary": return Theme.bgRaised
                    case "ghost": return "transparent"
                    case "danger": return Theme.error500
                    case "success": return Theme.success500
                    default: return Theme.primary500
                }
            }
            
            function getHoverColor() {
                switch (variant) {
                    case "primary": return Theme.primary600
                    case "secondary": return Theme.bgHover
                    case "ghost": return Theme.bgHover
                    case "danger": return Theme.error600
                    case "success": return Theme.success600
                    default: return Theme.primary600
                }
            }
            
            Text {
                anchors.centerIn: parent
                text: button.text
                color: {
                    if (button.variant === "secondary" || button.variant === "ghost") 
                        return button.variant === "ghost" && mouseArea.containsMouse ? 
                               Theme.textPrimary : Theme.textSecondary
                    return "white"
                }
                opacity: button.enabled ? 1 : 0.5
                font.pixelSize: button.size === "sm" ? 12 : (button.size === "lg" ? 15 : 14)
                font.weight: Font.Medium
            }
            
            MouseArea {
                id: mouseArea
                anchors.fill: parent
                enabled: button.enabled
                hoverEnabled: true
                onClicked: button.clicked()
            }
        }
    }
    
    // 数据卡片组件
    Component {
        id: dataCardComponent
        
        Rectangle {
            id: dataCard
            property string label: "温度"
            property string value: "25.5"
            property string unit: "°C"
            property string status: "online"  // online, offline, warning
            property string trend: "up"        // up, down, stable
            property string trendValue: "+2.3%"
            
            width: 200
            height: 140
            radius: 12
            
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.bgRaised }
                GradientStop { position: 1.0; color: Theme.bgOverlay }
            }
            
            border.color: Theme.borderDefault
            border.width: 1
            
            Rectangle {
                id: topBar
                width: parent.width
                height: 3
                radius: 0
                
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Theme.primary500 }
                    GradientStop { position: 1.0; color: Theme.accent500 }
                }
            }
            
            // 状态指示器
            Rectangle {
                id: statusDot
                width: 10
                height: 10
                radius: 5
                anchors { top: parent.top; right: parent.right; margins: 16 }
                
                color: {
                    switch (dataCard.status) {
                        case "online": return Theme.success500
                        case "offline": return Theme.error500
                        case "warning": return Theme.warning500
                        default: return Theme.success500
                    }
                }
                
                SequentialAnimationGroup {
                    running: dataCard.status !== "offline"
                    loops: Animation.Infinite
                    
                    PropertyAnimation {
                        target: statusDot
                        property: "opacity"
                        from: 1
                        to: 0.5
                        duration: 750
                    }
                    PropertyAnimation {
                        target: statusDot
                        property: "opacity"
                        from: 0.5
                        to: 1
                        duration: 750
                    }
                }
            }
            
            Column {
                anchors { left: parent.left; top: topBar.bottom; margins: 16 }
                spacing: 8
                
                Text {
                    text: dataCard.label.toUpperCase()
                    color: Theme.textSecondary
                    font.pixelSize: 10
                    font.weight: Font.Medium
                    letter.spacing: 0.05
                }
                
                Row {
                    spacing: 4
                    
                    Text {
                        text: dataCard.value
                        color: Theme.textPrimary
                        font.pixelSize: 24
                        font.weight: Font.Bold
                        font.family: "Courier New"
                    }
                    
                    Text {
                        text: dataCard.unit
                        color: Theme.textSecondary
                        font.pixelSize: 14
                        anchors.baseline: parent.baseline
                    }
                }
                
                Row {
                    spacing: 4
                    
                    Rectangle {
                        width: 14
                        height: 14
                        radius: 1
                        color: "transparent"
                        
                        Canvas {
                            anchors.fill: parent
                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.strokeStyle = parent.trendColor
                                ctx.lineWidth = 2
                                if (dataCard.trend === "up") {
                                    ctx.beginPath()
                                    ctx.moveTo(0, height)
                                    ctx.lineTo(width/2, 0)
                                    ctx.lineTo(width, height)
                                    ctx.stroke()
                                } else if (dataCard.trend === "down") {
                                    ctx.beginPath()
                                    ctx.moveTo(0, 0)
                                    ctx.lineTo(width/2, height)
                                    ctx.lineTo(width, 0)
                                    ctx.stroke()
                                }
                            }
                        }
                        
                        property color trendColor: {
                            if (dataCard.trend === "up") return Theme.success500
                            if (dataCard.trend === "down") return Theme.error500
                            return Theme.textSecondary
                        }
                    }
                    
                    Text {
                        text: dataCard.trendValue
                        color: {
                            if (dataCard.trend === "up") return Theme.success500
                            if (dataCard.trend === "down") return Theme.error500
                            return Theme.textSecondary
                        }
                        font.pixelSize: 12
                        font.weight: Font.Medium
                    }
                }
            }
            
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                
                onContainsMouseChanged: {
                    if (containsMouse) {
                        dataCard.scale = 1.02
                    } else {
                        dataCard.scale = 1
                    }
                }
                
                Behavior on scale {
                    NumberAnimation { duration: 150 }
                }
            }
        }
    }
    
    // 仪表盘组件
    Component {
        id: gaugeComponent
        
        Rectangle {
            id: gauge
            property string title: "仪表"
            property real value: 75  // 0-100
            property string status: "normal"  // normal, warning, danger
            
            width: 180
            height: 180
            radius: 12
            color: Theme.bgRaised
            border { color: Theme.borderDefault; width: 1 }
            
            Column {
                anchors.centerIn: parent
                spacing: 12
                
                Canvas {
                    width: 120
                    height: 120
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    onPaint: {
                        var ctx = getContext("2d")
                        var centerX = width / 2
                        var centerY = height / 2
                        var radius = 45
                        
                        // 背景圆
                        ctx.strokeStyle = Theme.borderDefault
                        ctx.lineWidth = 10
                        ctx.beginPath()
                        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
                        ctx.stroke()
                        
                        // 进度圆
                        var fillColor = Theme.primary500
                        if (gauge.status === "warning") fillColor = Theme.warning500
                        if (gauge.status === "danger") fillColor = Theme.error500
                        
                        ctx.strokeStyle = fillColor
                        ctx.lineWidth = 10
                        ctx.lineCap = "round"
                        ctx.beginPath()
                        var endAngle = (gauge.value / 100) * Math.PI * 2 - Math.PI / 2
                        ctx.arc(centerX, centerY, radius, -Math.PI / 2, endAngle)
                        ctx.stroke()
                    }
                }
                
                Text {
                    text: gauge.value + "%"
                    color: Theme.textPrimary
                    font.pixelSize: 20
                    font.weight: Font.Bold
                    font.family: "Courier New"
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
            
            Text {
                text: gauge.title
                color: Theme.textPrimary
                font.pixelSize: 13
                font.weight: Font.Medium
                anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; margins: 12 }
            }
        }
    }
    
    // 状态徽章组件
    Component {
        id: badgeComponent
        
        Rectangle {
            id: badge
            property string status: "success"  // success, warning, error, info, neutral
            property string text: "状态"
            property bool pulse: true
            
            implicitWidth: textItem.width + 12
            implicitHeight: 24
            radius: 12
            
            color: {
                switch (badge.status) {
                    case "success": return Qt.rgba(76, 175, 80, 0.15)
                    case "warning": return Qt.rgba(255, 193, 7, 0.15)
                    case "error": return Qt.rgba(244, 67, 54, 0.15)
                    case "info": return Qt.rgba(33, 150, 243, 0.15)
                    default: return Theme.bgOverlay
                }
            }
            
            border {
                width: 1
                color: {
                    switch (badge.status) {
                        case "success": return Qt.rgba(76, 175, 80, 0.3)
                        case "warning": return Qt.rgba(255, 193, 7, 0.3)
                        case "error": return Qt.rgba(244, 67, 54, 0.3)
                        case "info": return Qt.rgba(33, 150, 243, 0.3)
                        default: return Theme.borderDefault
                    }
                }
            }
            
            Row {
                anchors { fill: parent; margins: 6 }
                spacing: 4
                
                Rectangle {
                    width: 6
                    height: 6
                    radius: 3
                    anchors.verticalCenter: parent.verticalCenter
                    
                    color: {
                        switch (badge.status) {
                            case "success": return Theme.success500
                            case "warning": return Theme.warning500
                            case "error": return Theme.error500
                            case "info": return Theme.info500
                            default: return Theme.textSecondary
                        }
                    }
                    
                    SequentialAnimationGroup {
                        running: badge.pulse && badge.status !== "error"
                        loops: Animation.Infinite
                        
                        ScaleAnimator {
                            target: parent
                            from: 1
                            to: 1.2
                            duration: 750
                        }
                        ScaleAnimator {
                            target: parent
                            from: 1.2
                            to: 1
                            duration: 750
                        }
                    }
                }
                
                Text {
                    id: textItem
                    text: badge.text
                    color: {
                        switch (badge.status) {
                            case "success": return Theme.success500
                            case "warning": return Theme.warning500
                            case "error": return Theme.error500
                            case "info": return Theme.info500
                            default: return Theme.textSecondary
                        }
                    }
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    font.capitalization: Font.UpperCase
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }
    }
}
