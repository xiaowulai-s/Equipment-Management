// 工业设备管理系统 - 导航和表格组件库

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: navTableLibrary
    color: Theme.bgBase
    
    // ============== 导航菜单项 ==============
    Component {
        id: navItemComponent
        
        Rectangle {
            id: navItem
            property string label: ""
            property string icon: ""
            property bool active: false
            property int badgeCount: 0
            
            signal clicked()
            
            implicitWidth: 240
            implicitHeight: 40
            color: navItem.active ? Theme.primary50 : "transparent"
            border.color: "transparent"
            radius: 0
            
            Row {
                anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                spacing: 10
                
                // 图标区域
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
                            ctx.strokeStyle = navItem.active ? Theme.primary600 : Theme.textSecondary
                            ctx.lineWidth = 2
                            ctx.fillStyle = "transparent"
                            
                            // 简单的方块图标
                            ctx.strokeRect(2, 2, 20, 20)
                            if (navItem.active) {
                                ctx.fillRect(6, 6, 12, 12)
                            }
                        }
                    }
                }
                
                // 标签文本
                Text {
                    text: navItem.label
                    color: navItem.active ? Theme.primary600 : Theme.textPrimary
                    font.pixelSize: 14
                    font.weight: navItem.active ? Font.Medium : Font.Normal
                    anchors.verticalCenter: parent.verticalCenter
                    Layout.fillWidth: true
                }
                
                // 徽章
                Rectangle {
                    visible: navItem.badgeCount > 0
                    width: 24
                    height: 24
                    radius: 12
                    color: Theme.error500
                    anchors.verticalCenter: parent.verticalCenter
                    
                    Text {
                        anchors.centerIn: parent
                        text: navItem.badgeCount > 99 ? "..." : navItem.badgeCount
                        color: "white"
                        font.pixelSize: 12
                        font.weight: Font.Bold
                    }
                }
            }
            
            // 右侧边框高亮
            Rectangle {
                width: 3
                height: parent.height
                color: navItem.active ? Theme.primary600 : "transparent"
                anchors { right: parent.right; top: parent.top }
            }
            
            MouseArea {
                anchors.fill: parent
                onClicked: navItem.clicked()
                hoverEnabled: true
            }
        }
    }
    
    // ============== 设备树项 ==============
    Component {
        id: deviceTreeItemComponent
        
        Rectangle {
            id: deviceItem
            property string name: "设备"
            property string status: "online"  // online, offline, warning
            property bool expanded: false
            property bool isGroup: false
            property int indentLevel: 0
            
            signal clicked()
            signal expandToggled(bool expanded)
            
            implicitWidth: 240
            implicitHeight: 36
            color: "transparent"
            border.color: "transparent"
            radius: 0
            
            Row {
                anchors { fill: parent; margins: 4 }
                leftMargin: 12 + (deviceItem.indentLevel * 16)
                spacing: 8
                
                // 展开/收起箭头
                Rectangle {
                    width: 20
                    height: 20
                    radius: 3
                    color: "transparent"
                    anchors.verticalCenter: parent.verticalCenter
                    visible: deviceItem.isGroup
                    
                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.strokeStyle = Theme.textSecondary
                            ctx.lineWidth = 2
                            ctx.beginPath()
                            ctx.moveTo(6, 4)
                            ctx.lineTo(14, 10)
                            ctx.lineTo(6, 16)
                            ctx.stroke()
                            
                            // 旋转效果通过Canvas不好处理，这里简化表示
                        }
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            deviceItem.expanded = !deviceItem.expanded
                            deviceItem.expandToggled(deviceItem.expanded)
                        }
                    }
                }
                
                // 状态指示灯
                Rectangle {
                    width: 12
                    height: 12
                    radius: 6
                    color: deviceItem.status === "offline" ? Theme.gray300 :
                           deviceItem.status === "warning" ? Theme.warning400 :
                           Theme.success500
                    anchors.verticalCenter: parent.verticalCenter
                    
                    SequentialAnimationGroup {
                        running: deviceItem.status === "warning"
                        loops: Animation.Infinite
                        
                        OpacityAnimator {
                            target: parent
                            from: 1.0
                            to: 0.4
                            duration: 1000
                        }
                        OpacityAnimator {
                            target: parent
                            from: 0.4
                            to: 1.0
                            duration: 1000
                        }
                    }
                }
                
                // 设备名称
                Text {
                    text: deviceItem.name
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    font.weight: deviceItem.isGroup ? Font.Medium : Font.Normal
                    anchors.verticalCenter: parent.verticalCenter
                    Layout.fillWidth: true
                }
            }
            
            MouseArea {
                anchors.fill: parent
                propagateComposedEvents: true
                onClicked: deviceItem.clicked()
            }
        }
    }
    
    // ============== 数据表格 ==============
    Component {
        id: dataTableComponent
        
        Rectangle {
            id: tableContainer
            property var headers: ["地址", "功能码", "数值", "状态"]
            property var rows: []
            
            color: Theme.bgBase
            border.color: Theme.borderDefault
            border.width: 1
            radius: 6
            clip: true
            
            Column {
                anchors.fill: parent
                spacing: 0
                
                // 表头
                Rectangle {
                    width: parent.width
                    height: 44
                    color: Theme.bgRaised
                    border.bottom: Border { color: Theme.borderDefault; width: 1 }
                    
                    Row {
                        anchors { fill: parent; margins: 12 }
                        spacing: 16
                        
                        Repeater {
                            model: tableContainer.headers
                            
                            Text {
                                text: modelData
                                color: Theme.textSecondary
                                font.pixelSize: 13
                                font.weight: Font.Medium
                                width: (tableContainer.width - 24 - (tableContainer.headers.length - 1) * 16) / tableContainer.headers.length
                            }
                        }
                    }
                }
                
                // 表行
                ListView {
                    width: parent.width
                    height: parent.height - 44
                    model: tableContainer.rows
                    
                    delegate: Rectangle {
                        width: tableContainer.width
                        height: 44
                        color: index % 2 === 0 ? Theme.bgBase : Theme.bgRaised
                        border.bottom: Border { color: Theme.borderDefault; width: 1 }
                        
                        Row {
                            anchors { fill: parent; margins: 12 }
                            spacing: 16
                            
                            Text {
                                text: modelData.address || ""
                                color: Theme.textPrimary
                                font.pixelSize: 13
                                width: (tableContainer.width - 24 - (tableContainer.headers.length - 1) * 16) / tableContainer.headers.length
                            }
                            
                            Text {
                                text: modelData.funcCode || ""
                                color: Theme.textPrimary
                                font.pixelSize: 13
                                width: (tableContainer.width - 24 - (tableContainer.headers.length - 1) * 16) / tableContainer.headers.length
                            }
                            
                            Text {
                                text: modelData.value || ""
                                color: Theme.textPrimary
                                font.pixelSize: 13
                                font.family: "JetBrains Mono"
                                width: (tableContainer.width - 24 - (tableContainer.headers.length - 1) * 16) / tableContainer.headers.length
                            }
                            
                            Rectangle {
                                width: (tableContainer.width - 24 - (tableContainer.headers.length - 1) * 16) / tableContainer.headers.length
                                height: 24
                                radius: 4
                                color: modelData.status === "success" ? Theme.success50 :
                                       modelData.status === "warning" ? Theme.warning50 :
                                       Theme.error50
                                
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.status || ""
                                    color: modelData.status === "success" ? Theme.success600 :
                                           modelData.status === "warning" ? Theme.warning600 :
                                           Theme.error600
                                    font.pixelSize: 12
                                    font.weight: Font.Medium
                                }
                            }
                        }
                        
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onEntered: parent.color = Theme.primary50
                            onExited: parent.color = index % 2 === 0 ? Theme.bgBase : Theme.bgRaised
                        }
                    }
                }
            }
        }
    }
    
    // ============== 数据网格 ==============
    Component {
        id: dataGridComponent
        
        Rectangle {
            id: gridContainer
            property var items: []
            property int columns: 2
            
            color: Theme.bgBase
            
            GridLayout {
                anchors.fill: parent
                columns: gridContainer.columns
                columnSpacing: 16
                rowSpacing: 16
                
                Repeater {
                    model: gridContainer.items
                    
                    // 再次引用 dataCard 组件会更复杂
                    // 这里用简化版本
                    Rectangle {
                        Layout.fillWidth: true
                        height: 120
                        color: Theme.bgRaised
                        radius: 8
                        border {
                            color: Theme.borderDefault
                            width: 1
                        }
                        
                        Column {
                            anchors { fill: parent; margins: 12 }
                            spacing: 8
                            
                            Text {
                                text: modelData.label || ""
                                color: Theme.textSecondary
                                font.pixelSize: 12
                            }
                            
                            Text {
                                text: modelData.value || ""
                                color: Theme.textPrimary
                                font.pixelSize: 24
                                font.weight: Font.Bold
                            }
                            
                            Text {
                                text: modelData.unit || ""
                                color: Theme.textTertiary
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            }
        }
    }
}
