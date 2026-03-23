// 工业设备管理系统 - 通知和反馈组件库

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: notificationLibrary
    color: Theme.bgBase
    
    // ============== 吐司通知 ==============
    Component {
        id: toastComponent
        
        Rectangle {
            id: toast
            property string type: "success"  // success, error, warning, info
            property string message: "通知消息"
            property string title: ""
            property int duration: 3000
            
            signal closed()
            
            implicitWidth: 320
            implicitHeight: contentLayout.height + 16
            radius: 8
            color: toast.type === "success" ? Theme.success50 :
                   toast.type === "error" ? Theme.error50 :
                   toast.type === "warning" ? Theme.warning50 :
                   Theme.info50
            border {
                width: 1
                color: toast.type === "success" ? Theme.success200 :
                       toast.type === "error" ? Theme.error200 :
                       toast.type === "warning" ? Theme.warning200 :
                       Theme.info200
            }
            
            // 左侧颜色条
            Rectangle {
                width: 3
                height: parent.height
                radius: 8
                color: toast.type === "success" ? Theme.success500 :
                       toast.type === "error" ? Theme.error500 :
                       toast.type === "warning" ? Theme.warning500 :
                       Theme.info500
                anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
            }
            
            Row {
                id: contentLayout
                anchors { fill: parent; margins: 12; leftMargin: 16 }
                spacing: 12
                
                // 图标
                Rectangle {
                    width: 24
                    height: 24
                    radius: 4
                    color: "transparent"
                    anchors.verticalCenter: parent.verticalCenter
                    
                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.strokeStyle = toast.type === "success" ? Theme.success600 :
                                            toast.type === "error" ? Theme.error600 :
                                            toast.type === "warning" ? Theme.warning600 :
                                            Theme.info600
                            ctx.fillStyle = ctx.strokeStyle
                            ctx.lineWidth = 2
                            
                            if (toast.type === "success") {
                                // 对号
                                ctx.beginPath()
                                ctx.moveTo(3, 12)
                                ctx.lineTo(8, 17)
                                ctx.lineTo(21, 4)
                                ctx.stroke()
                            } else if (toast.type === "error") {
                                // 叉号
                                ctx.beginPath()
                                ctx.moveTo(4, 4)
                                ctx.lineTo(20, 20)
                                ctx.moveTo(20, 4)
                                ctx.lineTo(4, 20)
                                ctx.stroke()
                            } else if (toast.type === "warning") {
                                // 感叹号
                                ctx.beginPath()
                                ctx.arc(12, 6, 2, 0, Math.PI * 2)
                                ctx.fill()
                                ctx.fillRect(11, 10, 2, 10)
                            } else {
                                // 信息符号
                                ctx.beginPath()
                                ctx.arc(12, 12, 10, 0, Math.PI * 2)
                                ctx.stroke()
                                ctx.fillRect(11, 7, 2, 6)
                                ctx.fillRect(11, 15, 2, 2)
                            }
                        }
                    }
                }
                
                // 文本内容
                Column {
                    spacing: 2
                    anchors.verticalCenter: parent.verticalCenter
                    Layout.fillWidth: true
                    
                    Text {
                        text: toast.title
                        color: toast.type === "success" ? Theme.success600 :
                               toast.type === "error" ? Theme.error600 :
                               toast.type === "warning" ? Theme.warning600 :
                               Theme.info600
                        font.pixelSize: 14
                        font.weight: Font.Medium
                        visible: toast.title.length > 0
                    }
                    
                    Text {
                        text: toast.message
                        color: toast.type === "success" ? Theme.success700 :
                               toast.type === "error" ? Theme.error700 :
                               toast.type === "warning" ? Theme.warning700 :
                               Theme.info700
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
                
                // 关闭按钮
                Rectangle {
                    width: 24
                    height: 24
                    radius: 4
                    color: "transparent"
                    anchors.verticalCenter: parent.verticalCenter
                    
                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.strokeStyle = toast.type === "success" ? Theme.success400 :
                                            toast.type === "error" ? Theme.error400 :
                                            toast.type === "warning" ? Theme.warning400 :
                                            Theme.info400
                            ctx.lineWidth = 2
                            ctx.beginPath()
                            ctx.moveTo(4, 4)
                            ctx.lineTo(20, 20)
                            ctx.moveTo(20, 4)
                            ctx.lineTo(4, 20)
                            ctx.stroke()
                        }
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            fadeOut.start()
                        }
                    }
                }
            }
            
            // 自动关闭
            Timer {
                id: autoCloseTimer
                interval: toast.duration
                running: true
                onTriggered: {
                    fadeOut.start()
                }
            }
            
            // 淡出动画
            OpacityAnimator {
                id: fadeOut
                target: toast
                from: 1.0
                to: 0.0
                duration: 300
                onStopped: toast.closed()
            }
            
            // 滑入动画
            Component.onCompleted: {
                slideIn.start()
            }
            
            XAnimator {
                id: slideIn
                target: toast
                from: 340
                to: 0
                duration: 300
                easing.type: Easing.OutCubic
            }
        }
    }
    
    // ============== 提示气泡 ==============
    Component {
        id: tooltipComponent
        
        Rectangle {
            id: tooltip
            property string text: "提示内容"
            property string position: "top"  // top, bottom, left, right
            
            implicitWidth: Math.max(contentText.implicitWidth + 12, 80)
            implicitHeight: contentText.implicitHeight + 8
            radius: 4
            color: Theme.gray900
            opacity: 0.9
            
            Text {
                id: contentText
                anchors.centerIn: parent
                text: tooltip.text
                color: "white"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                width: Math.min(implicitWidth, 200)
            }
            
            // 三角箭头
            Canvas {
                id: arrow
                width: 8
                height: 4
                
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.fillStyle = Theme.gray900
                    ctx.beginPath()
                    
                    if (tooltip.position === "top") {
                        ctx.moveTo(0, 0)
                        ctx.lineTo(4, 4)
                        ctx.lineTo(8, 0)
                    } else if (tooltip.position === "bottom") {
                        ctx.moveTo(0, 4)
                        ctx.lineTo(4, 0)
                        ctx.lineTo(8, 4)
                    } else if (tooltip.position === "left") {
                        ctx.moveTo(4, 0)
                        ctx.lineTo(0, 4)
                        ctx.lineTo(4, 8)
                    } else {
                        ctx.moveTo(0, 0)
                        ctx.lineTo(4, 4)
                        ctx.lineTo(0, 8)
                    }
                    
                    ctx.fill()
                }
                
                anchors {
                    horizontalCenter: tooltip.position === "top" || tooltip.position === "bottom" ? parent.horizontalCenter : undefined
                    verticalCenter: tooltip.position === "left" || tooltip.position === "right" ? parent.verticalCenter : undefined
                    top: tooltip.position === "top" ? parent.bottom : undefined
                    bottom: tooltip.position === "bottom" ? parent.top : undefined
                    left: tooltip.position === "left" ? parent.right : undefined
                    right: tooltip.position === "right" ? parent.left : undefined
                }
            }
        }
    }
    
    // ============== 加载指示器 ==============
    Component {
        id: loadingComponent
        
        Rectangle {
            id: loadingContainer
            property string type: "spinner"  // spinner, dots, bar
            property string message: ""
            
            implicitWidth: column.width + 32
            implicitHeight: column.height + 32
            radius: 8
            color: Theme.gray900
            opacity: 0.95
            
            Column {
                id: column
                anchors.centerIn: parent
                spacing: 12
                horizontalAlignment: Column.AlignHCenter
                
                // 加载动画
                Rectangle {
                    width: 40
                    height: 40
                    color: "transparent"
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            var time = Date.now() % 2000
                            var progress = time / 2000
                            
                            if (loadingContainer.type === "spinner") {
                                ctx.strokeStyle = Theme.primary500
                                ctx.lineWidth = 3
                                ctx.beginPath()
                                ctx.arc(20, 20, 15, 0, Math.PI * 2 * progress)
                                ctx.stroke()
                            } else if (loadingContainer.type === "dots") {
                                var y = 20
                                for (var i = 0; i < 3; i++) {
                                    var alpha = (Math.sin(progress * Math.PI * 2 - i * Math.PI / 3) + 1) / 2
                                    ctx.fillStyle = "rgba(33, 150, 243, " + alpha + ")"
                                    ctx.beginPath()
                                    ctx.arc(12 + i * 8, y, 3, 0, Math.PI * 2)
                                    ctx.fill()
                                }
                            }
                        }
                        
                        SequentialAnimationGroup {
                            running: true
                            loops: Animation.Infinite
                            
                            PauseAnimation { duration: 50 }
                            
                            ScriptAction {
                                onTriggered: parent.requestPaint()
                            }
                        }
                    }
                }
                
                // 加载消息
                Text {
                    text: loadingContainer.message
                    color: "white"
                    font.pixelSize: 14
                    visible: loadingContainer.message.length > 0
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }
    }
    
    // ============== 对话框确认按钮组 ==============
    Component {
        id: dialogButtonsComponent
        
        Row {
            id: buttonGroup
            property string primaryText: "确认"
            property string secondaryText: "取消"
            
            signal primaryClicked()
            signal secondaryClicked()
            
            spacing: 12
            
            Rectangle {
                width: 100
                height: 36
                radius: 6
                color: Theme.bgRaised
                border {
                    color: Theme.borderDefault
                    width: 1
                }
                
                Text {
                    anchors.centerIn: parent
                    text: buttonGroup.secondaryText
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    font.weight: Font.Medium
                }
                
                MouseArea {
                    anchors.fill: parent
                    onClicked: buttonGroup.secondaryClicked()
                }
            }
            
            Rectangle {
                width: 100
                height: 36
                radius: 6
                color: Theme.primary500
                border.color: "transparent"
                
                Text {
                    anchors.centerIn: parent
                    text: buttonGroup.primaryText
                    color: "white"
                    font.pixelSize: 14
                    font.weight: Font.Medium
                }
                
                MouseArea {
                    anchors.fill: parent
                    onClicked: buttonGroup.primaryClicked()
                }
            }
        }
    }
}
