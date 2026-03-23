import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: configManagement
    width: parent.width
    height: parent.height
    color: "#161B22"
    radius: 8
    border.width: 1
    border.color: "#30363D"
    clip: true

    // 颜色定义
    property color colorPrimary: "#2196F3"
    property color colorBgOverlay: "#1C2128"
    property color colorBgHover: "#21262D"
    property color colorBorder: "#30363D"
    property color textPrimary: "#E6EDF3"
    property color textSecondary: "#8B949E"
    property color textTertiary: "#6E7681"

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // 标题
        Text {
            text: "配置管理"
            color: textPrimary
            font.pixelSize: 24
            font.family: "Inter, sans-serif"
            font.weight: Font.Bold
        }

        // 配置内容
        SwipeView {
            id: configSwipeView
            width: parent.width
            height: parent.height - 40
            clip: true

            // 系统设置页面
            Page {
                id: systemSettingsPage

                Column {
                    anchors.fill: parent
                    spacing: 16

                    Text {
                        text: "系统设置"
                        color: textPrimary
                        font.pixelSize: 18
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                    }

                    // 通信设置
                    Rectangle {
                        width: parent.width
                        padding: 12
                        color: colorBgOverlay
                        radius: 6

                        Text {
                            text: "通信设置"
                            color: textPrimary
                            font.pixelSize: 14
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Bold
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                        }

                        Column {
                            anchors.fill: parent
                            anchors.topMargin: 12
                            spacing: 8

                            Row {
                                Text {
                                    width: 120
                                    text: "更新间隔"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                }

                                TextField {
                                    id: updateIntervalField
                                    width: 100
                                    height: 32
                                    text: backend ? backend.getSystemConfig("update_interval") : "1000"
                                    placeholderText: "1000"
                                    font.family: "Inter, sans-serif"
                                    font.pixelSize: 13
                                }

                                Text {
                                    text: "ms"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                    anchors.leftMargin: 8
                                }
                            }

                            Row {
                                Text {
                                    width: 120
                                    text: "超时时间"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                }

                                TextField {
                                    id: timeoutField
                                    width: 100
                                    height: 32
                                    text: backend ? backend.getSystemConfig("timeout") : "5000"
                                    placeholderText: "5000"
                                    font.family: "Inter, sans-serif"
                                    font.pixelSize: 13
                                }

                                Text {
                                    text: "ms"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                    anchors.leftMargin: 8
                                }
                            }
                        }
                    }

                    // 日志设置
                    Rectangle {
                        width: parent.width
                        padding: 12
                        color: colorBgOverlay
                        radius: 6

                        Text {
                            text: "日志设置"
                            color: textPrimary
                            font.pixelSize: 14
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Bold
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                        }

                        Column {
                            anchors.fill: parent
                            anchors.topMargin: 12
                            spacing: 8

                            Row {
                                Text {
                                    width: 120
                                    text: "日志级别"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                }

                                Dropdown {
                                    id: logLevelDropdown
                                    width: 150
                                    height: 32
                                    currentIndex: backend ? {
                                        backend.getSystemConfig("log_level") === "DEBUG" ? 0 :
                                        backend.getSystemConfig("log_level") === "INFO" ? 1 :
                                        backend.getSystemConfig("log_level") === "WARNING" ? 2 :
                                        3
                                    } : 1
                                    model: ["DEBUG", "INFO", "WARNING", "ERROR"]
                                }
                            }

                            Row {
                                Text {
                                    width: 120
                                    text: "日志文件大小"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                }

                                TextField {
                                    id: logSizeField
                                    width: 100
                                    height: 32
                                    text: backend ? backend.getSystemConfig("log_max_size") : "50"
                                    placeholderText: "50"
                                    font.family: "Inter, sans-serif"
                                    font.pixelSize: 13
                                }

                                Text {
                                    text: "MB"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                    anchors.leftMargin: 8
                                }
                            }
                        }
                    }

                    // 保存按钮
                    Row {
                        anchors.right: parent.right
                        spacing: 8

                        Button {
                            id: cancelButton
                            text: "取消"
                            buttonStyleName: "ghost"
                            size: "md"
                            onClicked: {
                                // 重置字段
                                updateIntervalField.text = backend ? backend.getSystemConfig("update_interval") : "1000"
                                timeoutField.text = backend ? backend.getSystemConfig("timeout") : "5000"
                                logLevelDropdown.currentIndex = backend ? {
                                    backend.getSystemConfig("log_level") === "DEBUG" ? 0 :
                                    backend.getSystemConfig("log_level") === "INFO" ? 1 :
                                    backend.getSystemConfig("log_level") === "WARNING" ? 2 :
                                    3
                                } : 1
                                logSizeField.text = backend ? backend.getSystemConfig("log_max_size") : "50"
                            }
                        }

                        Button {
                            id: saveButton
                            text: "保存"
                            buttonStyleName: "primary"
                            size: "md"
                            onClicked: {
                                if (backend) {
                                    // 保存系统配置
                                    backend.setSystemConfig("update_interval", updateIntervalField.text)
                                    backend.setSystemConfig("timeout", timeoutField.text)
                                    backend.setSystemConfig("log_level", logLevelDropdown.model[logLevelDropdown.currentIndex])
                                    backend.setSystemConfig("log_max_size", logSizeField.text)
                                    
                                    // 保存用户设置
                                    backend.saveUserSettings()
                                    
                                    // 显示成功信息
                                    backend.systemMessage("success", "配置已保存")
                                }
                            }
                        }
                    }
                }
            }

            // 用户设置页面
            Page {
                id: userSettingsPage

                Column {
                    anchors.fill: parent
                    spacing: 16

                    Text {
                        text: "用户设置"
                        color: textPrimary
                        font.pixelSize: 18
                        font.family: "Inter, sans-serif"
                        font.weight: Font.Bold
                    }

                    // 主题设置
                    Rectangle {
                        width: parent.width
                        padding: 12
                        color: colorBgOverlay
                        radius: 6

                        Text {
                            text: "主题设置"
                            color: textPrimary
                            font.pixelSize: 14
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Bold
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                        }

                        Column {
                            anchors.fill: parent
                            anchors.topMargin: 12
                            spacing: 8

                            Row {
                                Text {
                                    width: 120
                                    text: "主题模式"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                }

                                Dropdown {
                                    id: themeDropdown
                                    width: 150
                                    height: 32
                                    currentIndex: backend ? (backend.getUserSetting("theme") === "dark" ? 0 : 1) : 0
                                    model: ["深色主题", "浅色主题"]
                                }
                            }
                        }
                    }

                    // 显示设置
                    Rectangle {
                        width: parent.width
                        padding: 12
                        color: colorBgOverlay
                        radius: 6

                        Text {
                            text: "显示设置"
                            color: textPrimary
                            font.pixelSize: 14
                            font.family: "Inter, sans-serif"
                            font.weight: Font.Bold
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                        }

                        Column {
                            anchors.fill: parent
                            anchors.topMargin: 12
                            spacing: 8

                            Row {
                                Text {
                                    width: 120
                                    text: "文字大小"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                }

                                Dropdown {
                                    id: fontSizeDropdown
                                    width: 150
                                    height: 32
                                    currentIndex: backend ? {
                                        backend.getUserSetting("font_size") === "small" ? 0 :
                                        backend.getUserSetting("font_size") === "medium" ? 1 :
                                        2
                                    } : 1
                                    model: ["小", "中", "大"]
                                }
                            }

                            Row {
                                Text {
                                    width: 120
                                    text: "自动刷新"
                                    color: textSecondary
                                    font.pixelSize: 13
                                    font.family: "Inter, sans-serif"
                                }

                                Switch {
                                    id: autoRefreshSwitch
                                    checked: backend ? (backend.getUserSetting("auto_refresh") === "true") : true
                                }
                            }
                        }
                    }

                    // 保存按钮
                    Row {
                        anchors.right: parent.right
                        spacing: 8

                        Button {
                            id: userCancelButton
                            text: "取消"
                            buttonStyleName: "ghost"
                            size: "md"
                            onClicked: {
                                // 重置字段
                                themeDropdown.currentIndex = backend ? (backend.getUserSetting("theme") === "dark" ? 0 : 1) : 0
                                fontSizeDropdown.currentIndex = backend ? {
                                    backend.getUserSetting("font_size") === "small" ? 0 :
                                    backend.getUserSetting("font_size") === "medium" ? 1 :
                                    2
                                } : 1
                                autoRefreshSwitch.checked = backend ? (backend.getUserSetting("auto_refresh") === "true") : true
                            }
                        }

                        Button {
                            id: userSaveButton
                            text: "保存"
                            buttonStyleName: "primary"
                            size: "md"
                            onClicked: {
                                if (backend) {
                                    // 保存用户设置
                                    backend.setUserSetting("theme", themeDropdown.currentIndex === 0 ? "dark" : "light")
                                    backend.setUserSetting("font_size", fontSizeDropdown.currentIndex === 0 ? "small" : fontSizeDropdown.currentIndex === 1 ? "medium" : "large")
                                    backend.setUserSetting("auto_refresh", autoRefreshSwitch.checked ? "true" : "false")
                                    backend.saveUserSettings()
                                    
                                    // 显示成功信息
                                    backend.systemMessage("success", "用户设置已保存")
                                }
                            }
                        }
                    }
                }
            }
        }

        // 页面指示器
        PageIndicator {
            id: configPageIndicator
            currentIndex: configSwipeView.currentIndex
            count: configSwipeView.count
            anchors.horizontalCenter: parent.horizontalCenter
            indicator.width: 8
            indicator.height: 8
            indicator.color: textTertiary
            indicator.selectedColor: colorPrimary
        }
    }
}
