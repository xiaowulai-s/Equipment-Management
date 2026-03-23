// 工业设备管理系统 - 主题管理器
// Theme Manager - Supports Dark/Light Theme Switching

import QtQuick 2.15

QtObject {
    id: themeManager

    property bool isDarkTheme: true

    // ==================== 深色主题颜色 ====================
    readonly property color darkBgBase:       "#0F1419"
    readonly property color darkBgRaised:     "#161B22"
    readonly property color darkBgOverlay:     "#1C2128"
    readonly property color darkBgHover:       "#21262D"
    readonly property color darkBgActive:      "#30363D"
    readonly property color darkTextPrimary:   "#E6EDF3"
    readonly property color darkTextSecondary: "#8B949E"
    readonly property color darkTextTertiary: "#6E7681"
    readonly property color darkBorderDefault: "#30363D"
    readonly property color darkBorderMuted:   "#21262D"
    readonly property color darkBorderAccent:  "#388BFD"

    // ==================== 浅色主题颜色 ====================
    readonly property color lightBgBase:       "#FFFFFF"
    readonly property color lightBgRaised:     "#F6F8FA"
    readonly property color lightBgOverlay:     "#FFFFFF"
    readonly property color lightBgHover:       "#F3F4F6"
    readonly property color lightBgActive:      "#E5E7EB"
    readonly property color lightTextPrimary:   "#1F2937"
    readonly property color lightTextSecondary: "#6B7280"
    readonly property color lightTextTertiary: "#9CA3AF"
    readonly property color lightBorderDefault: "#D1D5DB"
    readonly property color lightBorderMuted:   "#E5E7EB"
    readonly property color lightBorderAccent: "#2563EB"

    // ==================== 当前主题颜色 ====================
    property color bgBase:       isDarkTheme ? darkBgBase : lightBgBase
    property color bgRaised:     isDarkTheme ? darkBgRaised : lightBgRaised
    property color bgOverlay:     isDarkTheme ? darkBgOverlay : lightBgOverlay
    property color bgHover:       isDarkTheme ? darkBgHover : lightBgHover
    property color bgActive:      isDarkTheme ? darkBgActive : lightBgActive
    property color textPrimary:   isDarkTheme ? darkTextPrimary : lightTextPrimary
    property color textSecondary: isDarkTheme ? darkTextSecondary : lightTextSecondary
    property color textTertiary:  isDarkTheme ? darkTextTertiary : lightTextTertiary
    property color borderDefault:  isDarkTheme ? darkBorderDefault : lightBorderDefault
    property color borderMuted:    isDarkTheme ? darkBorderMuted : lightBorderMuted
    property color borderAccent:   isDarkTheme ? darkBorderAccent : lightBorderAccent

    // ==================== 主色调 (两者相同) ====================
    readonly property color primary50:  "#E3F2FD"
    readonly property color primary100: "#BBDEFB"
    readonly property color primary200: "#90CAF9"
    readonly property color primary300: "#64B5F6"
    readonly property color primary400: "#42A5F5"
    readonly property color primary500: "#2196F3"
    readonly property color primary600: "#1E88E5"
    readonly property color primary700: "#1976D2"
    readonly property color primary800: "#1565C0"
    readonly property color primary900: "#0D47A1"

    // ==================== 辅助色 ====================
    readonly property color accent400: "#26C6DA"
    readonly property color accent500: "#00BCD4"
    readonly property color accent600: "#00ACC1"

    // ==================== 功能色 ====================
    readonly property color success50:  "#E8F5E9"
    readonly property color success400: "#66BB6A"
    readonly property color success500: "#4CAF50"
    readonly property color success600: "#43A047"

    readonly property color warning50:  "#FFF8E1"
    readonly property color warning400: "#FFCA28"
    readonly property color warning500: "#FFC107"
    readonly property color warning600: "#FFB300"

    readonly property color error50:    "#FFEBEE"
    readonly property color error400:   "#EF5350"
    readonly property color error500:   "#F44336"
    readonly property color error600:   "#E53935"

    readonly property color info50:     "#E3F2FD"
    readonly property color info400:    "#42A5F5"
    readonly property color info500:    "#2196F3"

    // ==================== 状态指示灯 ====================
    readonly property color statusOnline:  "#3FB950"
    readonly property color statusOffline: "#F85149"
    readonly property color statusWarning: "#D29922"

    // ==================== 发光效果 ====================
    readonly property color glowSuccess: "#4CAF50"
    readonly property color glowWarning: "#FFC107"
    readonly property color glowError:   "#F44336"
    readonly property color glowPrimary: "#2196F3"

    // ==================== 字体定义 ====================
    readonly property string fontSans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    readonly property string fontMono: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"

    // ==================== 字号定义 ====================
    readonly property real fontDisplay:  2.5
    readonly property real fontH1:       2.0
    readonly property real fontH2:       1.5
    readonly property real fontH3:       1.25
    readonly property real fontH4:       1.125
    readonly property real fontBodyLg:   1.0
    readonly property real fontBody:     0.9375
    readonly property real fontBodySm:   0.875
    readonly property real fontCaption:  0.8125
    readonly property real fontDataLg:   2.0
    readonly property real fontData:     1.5

    // ==================== 间距定义 ====================
    readonly property real space1:  4
    readonly property real space2:  8
    readonly property real space3:  12
    readonly property real space4:  16
    readonly property real space5:  20
    readonly property real space6:  24
    readonly property real space8:  32
    readonly property real space10: 40
    readonly property real space12: 48
    readonly property real space16: 64

    // ==================== 圆角定义 ====================
    readonly property real radiusSm:   4
    readonly property real radiusMd:   6
    readonly property real radiusLg:   8
    readonly property real radiusXl:   12
    readonly property real radius2xl: 16
    readonly property real radiusFull: 9999

    // ==================== 动画时长 ====================
    readonly property int durationInstant: 50
    readonly property int durationFast:   150
    readonly property int durationNormal: 250
    readonly property int durationSlow:   400
    readonly property int durationSlower: 600

    // ==================== 主题切换方法 ====================
    function toggleTheme() {
        isDarkTheme = !isDarkTheme
    }

    function setDarkTheme() {
        isDarkTheme = true
    }

    function setLightTheme() {
        isDarkTheme = false
    }
}
