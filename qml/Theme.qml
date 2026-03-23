// 工业设备管理系统 - 主题常量定义
// Theme Constants based on UI设计方案.md

import QtQuick 2.15

QtObject {
    // ==================== 主色调 Primary Colors ====================
    readonly property color primary50:   "#E3F2FD"
    readonly property color primary100:  "#BBDEFB"
    readonly property color primary200:  "#90CAF9"
    readonly property color primary300: "#64B5F6"
    readonly property color primary400:  "#42A5F5"
    readonly property color primary500:  "#2196F3"  // 主色基准
    readonly property color primary600:  "#1E88E5"
    readonly property color primary700:  "#1976D2"
    readonly property color primary800:  "#1565C0"
    readonly property color primary900:  "#0D47A1"

    // ==================== 辅助色 Accent Colors ====================
    readonly property color accent400: "#26C6DA"
    readonly property color accent500: "#00BCD4"
    readonly property color accent600: "#00ACC1"

    // ==================== 功能色 Semantic Colors ====================
    // 成功状态 - 运行正常
    readonly property color success50:  "#E8F5E9"
    readonly property color success100: "#C8E6C9"
    readonly property color success400: "#66BB6A"
    readonly property color success500: "#4CAF50"
    readonly property color success600: "#43A047"

    // 警告状态 - 需要注意
    readonly property color warning50:  "#FFF8E1"
    readonly property color warning100: "#FFECB3"
    readonly property color warning400: "#FFCA28"
    readonly property color warning500: "#FFC107"
    readonly property color warning600: "#FFB300"

    // 错误状态 - 故障/离线
    readonly property color error50:    "#FFEBEE"
    readonly property color error100:   "#FFCDD2"
    readonly property color error400:   "#EF5350"
    readonly property color error500:   "#F44336"
    readonly property color error600:   "#E53935"

    // 信息状态
    readonly property color info50:     "#E3F2FD"
    readonly property color info100:    "#BBDEFB"
    readonly property color info400:    "#42A5F5"
    readonly property color info500:    "#2196F3"

    // ==================== 灰度系统 Neutral Colors ====================
    readonly property color gray25:   "#FCFCFD"
    readonly property color gray50:   "#F9FAFB"
    readonly property color gray100:  "#F3F4F6"
    readonly property color gray200:  "#E5E7EB"
    readonly property color gray300:  "#D1D5DB"
    readonly property color gray400:  "#9CA3AF"
    readonly property color gray500:  "#6B7280"
    readonly property color gray600:  "#4B5563"
    readonly property color gray700:  "#374151"
    readonly property color gray800:  "#1F2937"
    readonly property color gray900:  "#111827"

    // ==================== 深色主题背景 Dark Theme ====================
    readonly property color bgBase:       "#0F1419"
    readonly property color bgRaised:     "#161B22"
    readonly property color bgOverlay:    "#1C2128"
    readonly property color bgHover:      "#21262D"
    readonly property color bgActive:     "#30363D"

    // 深色文本
    readonly property color textPrimary:   "#E6EDF3"
    readonly property color textSecondary:  "#8B949E"
    readonly property color textTertiary:   "#6E7681"
    readonly property color textInverse:    "#0D1117"

    // 深色边框
    readonly property color borderDefault:  "#30363D"
    readonly property color borderMuted:    "#21262D"
    readonly property color borderAccent:    "#388BFD"

    // ==================== 状态指示灯 ====================
    readonly property color statusOnline:  "#3FB950"
    readonly property color statusOffline: "#F85149"
    readonly property color statusWarning:  "#D29922"

    // ==================== 阴影颜色 ====================
    readonly property color shadowColor:  "rgba(0, 0, 0, 0.4)"
    readonly property color overlayColor: "rgba(0, 0, 0, 0.6)"

    // ==================== 发光效果 ====================
    readonly property color glowSuccess: "#4CAF50"
    readonly property color glowWarning: "#FFC107"
    readonly property color glowError:   "#F44336"
    readonly property color glowPrimary:  "#2196F3"

    // ==================== 字体定义 ====================
    readonly property string fontSans:  "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    readonly property string fontMono: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"

    // ==================== 字号定义 ====================
    readonly property real fontDisplay:  2.5   // 40px
    readonly property real fontH1:       2.0   // 32px
    readonly property real fontH2:        1.5   // 24px
    readonly property real fontH3:        1.25  // 20px
    readonly property real fontH4:        1.125 // 18px
    readonly property real fontBodyLg:   1.0   // 16px
    readonly property real fontBody:      0.9375 // 15px
    readonly property real fontBodySm:   0.875  // 14px
    readonly property real fontCaption:   0.8125 // 13px
    readonly property real fontDataLg:    2.0   // 32px
    readonly property real fontData:      1.5   // 24px

    // ==================== 间距定义 ====================
    readonly property real space0:   0
    readonly property real spacePx:  1
    readonly property real space1:   4
    readonly property real space1_5: 6
    readonly property real space2:   8
    readonly property real space2_5: 10
    readonly property real space3:   12
    readonly property real space3_5: 14
    readonly property real space4:   16
    readonly property real space5:   20
    readonly property real space6:   24
    readonly property real space8:   32
    readonly property real space10:  40
    readonly property real space12:  48
    readonly property real space16:  64

    // ==================== 圆角定义 ====================
    readonly property real radiusNone:  0
    readonly property real radiusSm:   4
    readonly property real radiusMd:   6
    readonly property real radiusLg:   8
    readonly property real radiusXl:   12
    readonly property real radius2xl:  16
    readonly property real radiusFull:  9999

    // ==================== 动画时长 ====================
    readonly property int durationInstant: 50
    readonly property int durationFast:   150
    readonly property int durationNormal: 250
    readonly property int durationSlow:   400
    readonly property int durationSlower: 600
}