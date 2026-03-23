import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: dataExport
    width: parent.width
    height: parent.height
    color: "#161B22"
    radius: 8
    border.width: 1
    border.color: "#30363D"
    clip: true

    // 颜色定义
    property color colorPrimary: "#2196F3"
    property color colorSuccess: "#4CAF50"
    property color colorError: "#F44336"
    property color colorBgOverlay: "#1C2128"
    property color colorBgHover: "#21262D"
    property color colorBorder: "#30363D"
    property color textPrimary: "#E6EDF3"
    property color textSecondary: "#8B949E"
    property color textTertiary: "#6E7681"

    // 导出状态
    property bool exportInProgress: false
    property int exportProgress: 0

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // 标题
        Text {
            text: "数据导出"
            color: textPrimary
            font.pixelSize: 24
            font.family: "Inter, sans-serif"
            font.weight: Font.Bold
        }

        // 导出配置
        Rectangle {
            width: parent.width
            color: colorBgOverlay
            radius: 6

            Column {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                // 设备选择
                Column {
                    Text {
                        text: "设备选择"
                        color: textPrimary
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                    }

                    Row {
                        spacing: 8

                        Dropdown {
                            id: deviceDropdown
                            width: 200
                            height: 32
                            currentIndex: 0
                            model: backend ? backend.get_device_groups().map(function(group) {
                                return group.devices.map(function(device) {
                                    return device.name;
                                });
                            }).flat() : ["Pump-01", "Pump-02", "Pump-03", "Pump-04", "Pump-05"]
                        }

                        Text {
                            text: "所有设备"
                            color: textSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                        }

                        CheckBox {
                            id: allDevicesCheckbox
                            checked: false
                        }
                    }
                }

                // 寄存器选择
                Column {
                    Text {
                        text: "寄存器选择"
                        color: textPrimary
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                    }

                    Row {
                        spacing: 8

                        Dropdown {
                            id: registerDropdown
                            width: 200
                            height: 32
                            currentIndex: 0
                            model: backend ? backend.get_register_data().map(function(reg) {
                                return reg.variableName;
                            }) : ["温度传感器", "压力变送器", "流量计", "功率表", "频率", "效率"]
                        }

                        Text {
                            text: "所有寄存器"
                            color: textSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                        }

                        CheckBox {
                            id: allRegistersCheckbox
                            checked: true
                        }
                    }
                }

                // 时间范围
                Column {
                    Text {
                        text: "时间范围"
                        color: textPrimary
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                    }

                    Row {
                        spacing: 8

                        Text {
                            text: "开始时间:"
                            color: textSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                        }

                        TextField {
                            id: startTimeField
                            width: 150
                            height: 32
                            text: new Date(Date.now() - 24 * 60 * 60 * 1000).toLocaleString()
                            placeholderText: "YYYY-MM-DD HH:MM:SS"
                            font.family: "Inter, sans-serif"
                            font.pixelSize: 13
                        }

                        Text {
                            text: "结束时间:"
                            color: textSecondary
                            font.pixelSize: 13
                            font.family: "Inter, sans-serif"
                        }

                        TextField {
                            id: endTimeField
                            width: 150
                            height: 32
                            text: new Date().toLocaleString()
                            placeholderText: "YYYY-MM-DD HH:MM:SS"
                            font.family: "Inter, sans-serif"
                            font.pixelSize: 13
                        }
                    }
                }

                // 导出格式
                Column {
                    Text {
                        text: "导出格式"
                        color: textPrimary
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                    }

                    Column {
                        width: parent.width

                        property bool csvSelected: true
                        property bool excelSelected: false

                        Row {
                            spacing: 8

                            Button {
                                id: csvButton
                                text: "CSV格式"
                                buttonStyleName: csvSelected ? "primary" : "ghost"
                                width: 100
                                onClicked: {
                                    csvSelected = true
                                    excelSelected = false
                                }
                            }

                            Button {
                                id: excelButton
                                text: "Excel格式"
                                buttonStyleName: excelSelected ? "primary" : "ghost"
                                width: 100
                                onClicked: {
                                    excelSelected = true
                                    csvSelected = false
                                }
                            }
                        }
                    }
                }

                // 导出路径
                Column {
                    Text {
                        text: "导出路径"
                        color: textPrimary
                        font.pixelSize: 14
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                        anchors.left: parent.left
                        anchors.leftMargin: 4
                    }

                    Row {
                        spacing: 8

                        TextField {
                            id: exportPathField
                            width: 400
                            height: 32
                            text: "C:/export/" + new Date().toISOString().slice(0, 19).replace(/:/g, "-") + "." + (parent.csvSelected ? "csv" : "xlsx")
                            placeholderText: "请选择导出路径"
                            font.family: "Inter, sans-serif"
                            font.pixelSize: 13
                        }

                        Button {
                            id: browseButton
                            text: "浏览"
                            buttonStyleName: "ghost"
                            size: "md"
                            onClicked: {
                                // 这里应该调用文件选择对话框，但在QML中需要后端支持
                                // 暂时使用默认路径
                                exportPathField.text = "C:/export/" + new Date().toISOString().slice(0, 19).replace(/:/g, "-") + "." + (parent.csvSelected ? "csv" : "xlsx")
                            }
                        }
                    }
                }

                // 导出按钮和进度
                Column {
                    Row {
                        spacing: 8

                        // 导出按钮
                        Button {
                            id: exportButton
                            text: exportInProgress ? "导出中..." : "导出数据"
                            buttonStyleName: "primary"
                            size: "lg"
                            onClicked: {
                                if (!exportInProgress && backend) {
                                    startExport()
                                }
                            }
                            enabled: !exportInProgress
                        }

                        // 取消按钮
                        Button {
                            id: cancelButton
                            text: "取消"
                            buttonStyleName: "ghost"
                            size: "lg"
                            onClicked: {
                                if (exportInProgress && backend) {
                                    cancelExport()
                                }
                            }
                            enabled: exportInProgress
                        }
                    }

                    // 进度条
                    ProgressBar {
                        id: exportProgressBar
                        width: parent.width
                        height: 6
                        value: exportProgress / 100
                        visible: exportInProgress
                        anchors.top: parent.top
                        anchors.topMargin: 48

                        background: Rectangle {
                            color: colorBgHover
                            radius: 3
                        }

                        contentItem: Rectangle {
                            color: colorPrimary
                            radius: 3
                            width: exportProgressBar.width * exportProgressBar.value
                            height: exportProgressBar.height
                        }
                    }

                    // 进度文本
                    Text {
                        id: exportProgressText
                        text: "导出进度: " + exportProgress + "%"
                        color: textSecondary
                        font.pixelSize: 13
                        font.family: "Inter, sans-serif"
                        visible: exportInProgress
                        anchors.top: exportProgressBar.bottom
                        anchors.topMargin: 4
                    }
                }
            }
        }

        // 导出历史
        Rectangle {
            width: parent.width
            color: colorBgOverlay
            radius: 6

            Column {
                anchors.fill: parent
                anchors.margins: 16

                Text {
                    text: "导出历史"
                    color: textPrimary
                    font.pixelSize: 16
                    font.family: "Inter, sans-serif"
                    font.weight: Font.Bold
                    anchors.left: parent.left
                    anchors.leftMargin: 4
                }

                // 历史记录列表
                ListView {
                    id: exportHistoryList
                    width: parent.width
                    height: 150
                    clip: true
                    model: [
                        { fileName: "export_2026-03-22_10-30-00.csv", status: "success", size: "1.2 MB", time: "2026-03-22 10:30:00" },
                        { fileName: "export_2026-03-22_09-15-00.xlsx", status: "success", size: "2.5 MB", time: "2026-03-22 09:15:00" },
                        { fileName: "export_2026-03-21_16-45-00.csv", status: "error", size: "0 KB", time: "2026-03-21 16:45:00" }
                    ]

                    delegate: Rectangle {
                        width: parent.width
                        height: 40
                        color: "transparent"

                        Row {
                            spacing: 16
                            anchors.fill: parent
                            anchors.verticalCenter: parent.verticalCenter

                            // 文件名
                            Text {
                                text: model.fileName
                                color: textPrimary
                                font.pixelSize: 13
                                font.family: "Inter, sans-serif"
                                anchors.left: parent.left
                                anchors.leftMargin: 8
                            }

                            // 状态
                            StatusBadge {
                                status: model.status === "success" ? 0 : 2
                                width: 60
                                height: 20
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            // 文件大小
                            Text {
                                text: model.size
                                color: textSecondary
                                font.pixelSize: 12
                                font.family: "Inter, sans-serif"
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            // 导出时间
                            Text {
                                text: model.time
                                color: textTertiary
                                font.pixelSize: 12
                                font.family: "Inter, sans-serif"
                                anchors.right: parent.right
                                anchors.rightMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                // 这里应该调用文件打开功能
                                console.log("打开文件: " + model.fileName)
                            }
                        }
                    }
                }
            }
        }
    }

    // 导出成功提示
    Rectangle {
        id: successNotification
        width: 300
        height: 60
        radius: 8
        color: colorSuccess
        visible: false
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 20
        anchors.rightMargin: 20

        Text {
            anchors.centerIn: parent
            text: "数据导出成功!"
            color: "white"
            font.pixelSize: 14
            font.family: "Inter, sans-serif"
        }
    }

    // 导出失败提示
    Rectangle {
        id: errorNotification
        width: 300
        height: 60
        radius: 8
        color: colorError
        visible: false
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 20
        anchors.rightMargin: 20

        Text {
            anchors.centerIn: parent
            text: "数据导出失败!"
            color: "white"
            font.pixelSize: 14
            font.family: "Inter, sans-serif"
        }
    }

    // 开始导出
    function startExport() {
        if (!backend) return

        exportInProgress = true
        exportProgress = 0
        exportButton.text = "导出中..."
        exportProgressBar.visible = true
        exportProgressText.visible = true

        // 模拟导出进度
        var exportTimer = setInterval(function() {
            exportProgress += 5
            if (exportProgress >= 100) {
                clearInterval(exportTimer)
                exportInProgress = false
                exportProgress = 100
                exportButton.text = "导出数据"
                exportProgressBar.visible = false
                exportProgressText.visible = false

                // 调用后端导出函数
                var success = backend.exportHistoryData(
                    deviceDropdown.model[deviceDropdown.currentIndex],
                    allRegistersCheckbox.checked ? "" : "0x0001",
                    startTimeField.text,
                    endTimeField.text,
                    exportPathField.text,
                    true
                )

                // 显示结果
                if (success) {
                    showSuccessNotification()
                } else {
                    showErrorNotification()
                }
            }
        }, 200)
    }

    // 取消导出
    function cancelExport() {
        if (!backend) return

        exportInProgress = false
        exportProgress = 0
        exportButton.text = "导出数据"
        exportProgressBar.visible = false
        exportProgressText.visible = false

        // 这里应该调用后端取消函数
        backend.systemMessage("info", "导出已取消")
    }

    // 显示成功提示
    function showSuccessNotification() {
        successNotification.visible = true
        setTimeout(function() {
            successNotification.visible = false
        }, 3000)
    }

    // 显示失败提示
    function showErrorNotification() {
        errorNotification.visible = true
        setTimeout(function() {
            errorNotification.visible = false
        }, 3000)
    }
}
