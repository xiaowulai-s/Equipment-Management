// 工业设备管理系统 - 输入控件组件库

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../"

Rectangle {
    id: inputComponentLibrary
    color: Theme.bgBase
    
    // ============== 文本输入框 ==============
    Component {
        id: textInputComponent
        
        Rectangle {
            id: inputContainer
            property string placeholder: "请输入"
            property string text: ""
            property bool enabled: true
            property string inputValue: ""
            property string helperText: ""
            
            signal textChanged(string newText)
            
            implicitHeight: columnLayout.height + 8
            color: Theme.bgBase
            border.color: "transparent"
            radius: 0
            
            Column {
                id: columnLayout
                width: parent.width
                spacing: 4
                
                Text {
                    text: inputContainer.text
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    visible: inputContainer.text.length > 0
                }
                
                Rectangle {
                    width: parent.width
                    height: 36
                    radius: 6
                    color: Theme.bgRaised
                    border {
                        color: textInput.activeFocus ? Theme.primary500 : Theme.borderDefault
                        width: 1
                    }
                    
                    TextInput {
                        id: textInput
                        anchors { fill: parent; margins: 8 }
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.family: "Inter"
                        
                        Text {
                            anchors { fill: parent; margins: 8 }
                            text: inputContainer.placeholder
                            color: Theme.textTertiary
                            visible: !parent.text && !parent.activeFocus
                            font.pixelSize: 14
                            font.family: "Inter"
                            pointer-events: none
                        }
                        
                        onTextChanged: {
                            inputContainer.inputValue = text
                            inputContainer.textChanged(text)
                        }
                        
                        enabled: inputContainer.enabled
                    }
                }
                
                Text {
                    text: inputContainer.helperText
                    color: Theme.textTertiary
                    font.pixelSize: 12
                    visible: inputContainer.helperText.length > 0
                }
            }
        }
    }
    
    // ============== 下拉选择框 ==============
    Component {
        id: selectComponent
        
        Rectangle {
            id: selectContainer
            property string label: ""
            property var items: []
            property int currentIndex: 0
            property string currentValue: items.length > 0 ? items[currentIndex] : ""
            
            signal selected(int index, string value)
            
            implicitHeight: columnLayout.height + 8
            color: Theme.bgBase
            border.color: "transparent"
            radius: 0
            
            Column {
                id: columnLayout
                width: parent.width
                spacing: 4
                
                Text {
                    text: selectContainer.label
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    visible: selectContainer.label.length > 0
                }
                
                Rectangle {
                    width: parent.width
                    height: 36
                    radius: 6
                    color: Theme.bgRaised
                    border {
                        color: selectMouseArea.containsMouse ? Theme.primary500 : Theme.borderDefault
                        width: 1
                    }
                    
                    Row {
                        anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                        spacing: 8
                        
                        Text {
                            text: selectContainer.currentValue
                            color: Theme.textPrimary
                            font.pixelSize: 14
                            anchors.verticalCenter: parent.verticalCenter
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        
                        Canvas {
                            width: 16
                            height: 16
                            anchors.verticalCenter: parent.verticalCenter
                            
                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.strokeStyle = Theme.textTertiary
                                ctx.lineWidth = 2
                                ctx.beginPath()
                                ctx.moveTo(0, 6)
                                ctx.lineTo(width/2, 10)
                                ctx.lineTo(width, 6)
                                ctx.stroke()
                            }
                        }
                    }
                    
                    MouseArea {
                        id: selectMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            selectContainer.currentIndex = (selectContainer.currentIndex + 1) % selectContainer.items.length
                            selectContainer.selected(selectContainer.currentIndex, selectContainer.currentValue)
                        }
                    }
                }
            }
        }
    }
    
    // ============== 复选框 ==============
    Component {
        id: checkboxComponent
        
        Rectangle {
            id: checkboxContainer
            property string text: "选项"
            property bool checked: false
            
            signal toggled(bool checked)
            
            implicitWidth: rowLayout.width
            implicitHeight: 28
            color: "transparent"
            border.color: "transparent"
            radius: 0
            
            Row {
                id: rowLayout
                spacing: 8
                anchors.verticalCenter: parent.verticalCenter
                
                Rectangle {
                    id: checkBox
                    width: 18
                    height: 18
                    radius: 4
                    color: checkboxContainer.checked ? Theme.primary500 : "transparent"
                    border {
                        color: checkboxContainer.checked ? Theme.primary500 : Theme.borderDefault
                        width: 2
                    }
                    
                    Canvas {
                        anchors.fill: parent
                        visible: checkboxContainer.checked
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.strokeStyle = "white"
                            ctx.lineWidth = 2
                            ctx.beginPath()
                            ctx.moveTo(3, 9)
                            ctx.lineTo(6, 12)
                            ctx.lineTo(15, 3)
                            ctx.stroke()
                        }
                    }
                }
                
                Text {
                    text: checkboxContainer.text
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    checkboxContainer.checked = !checkboxContainer.checked
                    checkboxContainer.toggled(checkboxContainer.checked)
                }
            }
        }
    }
    
    // ============== 开关 ==============
    Component {
        id: toggleComponent
        
        Rectangle {
            id: toggleContainer
            property bool checked: false
            
            signal toggled(bool checked)
            
            implicitWidth: 44
            implicitHeight: 24
            radius: 12
            color: toggleContainer.checked ? Theme.primary500 : Theme.borderDefault
            border.color: "transparent"
            
            Rectangle {
                id: toggleThumb
                width: 20
                height: 20
                radius: 10
                color: "white"
                y: 2
                x: toggleContainer.checked ? parent.width - width - 2 : 2
                
                Behavior on x {
                    NumberAnimation { duration: 150 }
                }
                
                layer.enabled: true
                layer.effect: DropShadow {
                    id: shadowEffect
                    horizontalOffset: 0
                    verticalOffset: 1
                    radius: 3
                    samples: 7
                    color: Qt.rgba(0, 0, 0, 0.1)
                }
            }
            
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    toggleContainer.checked = !toggleContainer.checked
                    toggleContainer.toggled(toggleContainer.checked)
                }
            }
            
            Behavior on color {
                ColorAnimation { duration: 150 }
            }
        }
    }
    
    // ============== 进度条 ==============
    Component {
        id: progressBarComponent
        
        Rectangle {
            id: progressContainer
            property real value: 0.75  // 0-1
            property string status: "normal"  // normal, warning, danger
            
            implicitHeight: 8
            radius: 4
            color: Theme.borderDefault
            
            Rectangle {
                width: parent.width * progressContainer.value
                height: parent.height
                radius: parent.radius
                
                gradient: Gradient {
                    GradientStop { position: 0.0; 
                        color: progressContainer.status === "danger" ? Theme.error400 :
                               progressContainer.status === "warning" ? Theme.warning400 :
                               Theme.primary500
                    }
                    GradientStop { position: 1.0; 
                        color: progressContainer.status === "danger" ? Theme.error500 :
                               progressContainer.status === "warning" ? Theme.warning500 :
                               Theme.accent500
                    }
                }
                
                Behavior on width {
                    NumberAnimation { duration: 400; easing.type: Easing.OutCubic }
                }
            }
        }
    }
}
