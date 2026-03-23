# 工业设备管理系统 - UI设计方案

## 一、设计系统概述

本设计方案为工业设备管理系统打造一套专业、美观、易用的界面。设计语言融合了现代工业美学与Windows Fluent Design，强调信息层次、操作效率与视觉舒适度的平衡。

**核心设计原则：**
- 🎯 **信息密度适中** - 既不过于拥挤也不过于稀疏，保证关键数据一目了然
- 🔍 **层次分明** - 通过视觉权重引导用户注意力，重要信息优先呈现
- ⚡ **操作高效** - 常用操作路径最短，减少点击次数
- 🌙 **工业级配色** - 深色主题减少视觉疲劳，适合长时间监控
- ♿ **无障碍友好** - 符合WCAG AA标准，色对比度≥4.5:1

---

## 二、设计系统基础

### 2.1 色彩系统

#### 2.1.1 主色调 (Primary Colors)

```css
/* 品牌主色 - 科技蓝 */
--color-primary-50:  #E3F2FD;   /* 浅蓝背景 */
--color-primary-100: #BBDEFB;   /* 悬停背景 */
--color-primary-200: #90CAF9;   /* 次要强调 */
--color-primary-300: #64B5F6;   /* 边框 */
--color-primary-400: #42A5F5;   /* 图标 */
--color-primary-500: #2196F3;   /* 主色 (基准) */
--color-primary-600: #1E88E5;   /* 主色-深 */
--color-primary-700: #1976D2;   /* 主色-更深 */
--color-primary-800: #1565C0;   /* 主色-最深 */
--color-primary-900: #0D47A1;   /* 标题强调 */

/* 辅助色 - 青色 (数据可视化) */
--color-accent-400:  #26C6DA;
--color-accent-500:  #00BCD4;
--color-accent-600:  #00ACC1;
```

#### 2.1.2 功能色 (Semantic Colors)

```css
/* 成功状态 - 运行正常 */
--color-success-50:  #E8F5E9;
--color-success-100: #C8E6C9;
--color-success-400: #66BB6A;
--color-success-500: #4CAF50;   /* 正常-深 */
--color-success-600: #43A047;

/* 警告状态 - 需要注意 */
--color-warning-50:  #FFF8E1;
--color-warning-100: #FFECB3;
--color-warning-400: #FFCA28;
--color-warning-500: #FFC107;   /* 警告-深 */
--color-warning-600: #FFB300;

/* 错误状态 - 故障/离线 */
--color-error-50:    #FFEBEE;
--color-error-100:   #FFCDD2;
--color-error-400:   #EF5350;
--color-error-500:   #F44336;   /* 错误-深 */
--color-error-600:   #E53935;

/* 信息状态 - 提示/中性 */
--color-info-50:     #E3F2FD;
--color-info-100:    #BBDEFB;
--color-info-400:    #42A5F5;
--color-info-500:    #2196F3;   /* 信息-深 */
```

#### 2.1.3 中性色 (Neutral Colors)

```css
/* 灰度系统 */
--color-gray-25:   #FCFCFD;    /* 最浅背景 */
--color-gray-50:   #F9FAFB;    /* 页面背景 */
--color-gray-100:  #F3F4F6;    /* 卡片背景 */
--color-gray-200:  #E5E7EB;    /* 边框-浅 */
--color-gray-300:  #D1D5DB;    /* 边框-中 */
--color-gray-400:  #9CA3AF;    /* 占位符 */
--color-gray-500:  #6B7280;    /* 辅助文本 */
--color-gray-600:  #4B5563;    /* 正文文本 */
--color-gray-700:  #374151;    /* 标题文本 */
--color-gray-800:  #1F2937;    /* 深色文本 */
--color-gray-900:  #111827;    /* 最深文本 */
```

#### 2.1.4 深色主题背景

```css
[data-theme="dark"] {
  /* 深色背景层次 */
  --bg-base:       #0F1419;    /* 最深层 */
  --bg-raised:     #161B22;    /* 卡片/面板 */
  --bg-overlay:    #1C2128;    /* 弹窗/下拉 */
  --bg-hover:      #21262D;    /* 悬停态 */
  
  /* 深色文本 */
  --text-primary:  #E6EDF3;    /* 主要文本 */
  --text-secondary: #8B949E;   /* 次要文本 */
  --text-tertiary:  #6E7681;   /* 禁用/提示 */
  --text-inverse:   #0D1117;   /* 反色文本 */
  
  /* 深色边框 */
  --border-default: #30363D;   /* 默认边框 */
  --border-muted:   #21262D;   /* 弱边框 */
  --border-accent:  #388BFD;   /* 强调边框 */
}
```

### 2.2 字体系统

#### 2.2.1 字体族

```css
/* 主字体 - 界面文本 */
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* 等宽字体 - 数值/代码 */
--font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;

/* 数字专用 - 仪表盘数据 */
--font-numeric: 'Inter', 'Segoe UI', sans-serif;
```

#### 2.2.2 字体比例

```css
/* 标题层级 */
--text-display:  2.5rem;   /* 40px - 页面大标题 */
--text-h1:       2rem;      /* 32px - 模块标题 */
--text-h2:       1.5rem;    /* 24px - 卡片标题 */
--text-h3:       1.25rem;   /* 20px - 分组标题 */
--text-h4:       1.125rem;  /* 18px - 区块标题 */

/* 正文层级 */
--text-body-lg:  1rem;      /* 16px - 主要内容 */
--text-body:    0.9375rem; /* 15px - 默认正文 */
--text-body-sm: 0.875rem;  /* 14px - 次要信息 */
--text-caption: 0.8125rem; /* 13px - 说明文字 */

/* 数据展示 - 等宽数字 */
--text-data-lg:  2rem;      /* 32px - 仪表盘数值 */
--text-data:     1.5rem;    /* 24px - 关键数据 */
--text-data-sm:  1rem;      /* 16px - 表格数值 */
```

#### 2.2.3 字重与行高

```css
/* 字重 */
--font-normal:   400;       /* 正文 */
--font-medium:   500;       /* 标签/强调 */
--font-semibold: 600;       /* 标题 */
--font-bold:     700;       /* 重要数值 */

/* 行高 */
--leading-none:   1;        /* 紧凑数据 */
--leading-tight:  1.25;     /* 标题 */
--leading-normal: 1.5;      /* 正文 */
--leading-relaxed: 1.75;    /* 长文本 */

/* 字间距 */
--tracking-tight:  -0.025em; /* 标题 */
--tracking-normal: 0;        /* 正文 */
--tracking-wide:   0.025em;  /* 大写/标签 */
```

### 2.3 间距系统

#### 2.3.1 基础间距单位

基于 **4px** 网格系统的比例扩展：

```css
--space-0:   0;       /* 0px */
--space-px:  1px;    /* 1px */
--space-0.5: 0.125rem;  /* 2px */
--space-1:  0.25rem;   /* 4px */
--space-1.5: 0.375rem; /* 6px */
--space-2:  0.5rem;    /* 8px */
--space-2.5: 0.625rem; /* 10px */
--space-3:  0.75rem;   /* 12px */
--space-3.5: 0.875rem; /* 14px */
--space-4:  1rem;      /* 16px */
--space-5:  1.25rem;   /* 20px */
--space-6:  1.5rem;    /* 24px */
--space-8:  2rem;      /* 32px */
--space-10: 2.5rem;    /* 40px */
--space-12: 3rem;      /* 48px */
--space-16: 4rem;      /* 64px */
--space-20: 5rem;      /* 80px */
--space-24: 6rem;      /* 96px */
```

#### 2.3.2 间距应用规范

```css
/* 组件内间距 */
--padding-button: var(--space-3) var(--space-4);    /* 按钮内边距 */
--padding-input: var(--space-2) var(--space-3);     /* 输入框 */
--padding-card: var(--space-4);                      /* 卡片内边距 */
--padding-section: var(--space-6);                   /* 区块间距 */

/* 组件间间距 */
--gap-xs: var(--space-1);    /* 4px - 紧凑元素 */
--gap-sm: var(--space-2);    /* 8px - 关联元素 */
--gap-md: var(--space-4);    /* 16px - 分组元素 */
--gap-lg: var(--space-6);    /* 24px - 区块元素 */
--gap-xl: var(--space-8);    /* 32px - 页面区域 */
```

### 2.4 圆角系统

```css
/* 圆角比例 */
--radius-none: 0;
--radius-sm:   0.25rem;   /* 4px - 小元素 */
--radius-md:   0.375rem;  /* 6px - 默认 */
--radius-lg:   0.5rem;    /* 8px - 卡片 */
--radius-xl:   0.75rem;   /* 12px - 大卡片 */
--radius-2xl:  1rem;       /* 16px - 特殊 */
--radius-full: 9999px;     /* 圆形 */

/* 圆角应用 */
--radius-button: var(--radius-md);
--radius-input: var(--radius-md);
--radius-card: var(--radius-lg);
--radius-modal: var(--radius-xl);
--radius-avatar: var(--radius-full);
--radius-badge: var(--radius-sm);
```

### 2.5 阴影系统

```css
/* 阴影层次 */
--shadow-xs:  0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-sm:  0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
--shadow-md:  0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
--shadow-lg:  0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
--shadow-xl:  0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);

/* 工业风格阴影 (带蓝调) */
--shadow-industrial-sm: 0 2px 4px rgba(33, 150, 243, 0.08);
--shadow-industrial-md: 0 4px 12px rgba(33, 150, 243, 0.12);
--shadow-industrial-lg: 0 8px 24px rgba(33, 150, 243, 0.16);

/* 发光效果 (用于状态指示) */
--glow-success: 0 0 12px rgba(76, 175, 80, 0.5);
--glow-warning: 0 0 12px rgba(255, 193, 7, 0.5);
--glow-error:   0 0 12px rgba(244, 67, 54, 0.5);
--glow-primary: 0 0 12px rgba(33, 150, 243, 0.5);
```

### 2.6 动效系统

```css
/* 过渡时长 */
--duration-instant: 50ms;   /* 立即响应 */
--duration-fast: 150ms;     /* 快速交互 */
--duration-normal: 250ms;    /* 标准动画 */
--duration-slow: 400ms;     /* 强调动画 */
--duration-slower: 600ms;    /* 大型过渡 */

/* 缓动函数 */
--ease-linear:   linear;
--ease-in:       cubic-bezier(0.4, 0, 1, 1);
--ease-out:      cubic-bezier(0, 0, 0.2, 1);
--ease-in-out:   cubic-bezier(0.4, 0, 0.2, 1);
--ease-bounce:   cubic-bezier(0.68, -0.55, 0.265, 1.55);

/* 通用过渡 */
--transition-base: all var(--duration-fast) var(--ease-out);
--transition-colors: background-color var(--duration-fast) var(--ease-out), 
                      border-color var(--duration-fast) var(--ease-out),
                      color var(--duration-fast) var(--ease-out),
                      box-shadow var(--duration-fast) var(--ease-out);
```

---

## 三、组件库设计

### 3.1 按钮 (Button)

#### 3.1.1 按钮变体

```css
/* 主按钮 - 主要操作 */
.btn-primary {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-600));
  color: white;
  border: 1px solid transparent;
  box-shadow: var(--shadow-industrial-sm);
  transition: var(--transition-colors);
}

.btn-primary:hover {
  background: linear-gradient(135deg, var(--color-primary-600), var(--color-primary-700));
  transform: translateY(-1px);
  box-shadow: var(--shadow-industrial-md);
}

.btn-primary:active {
  transform: translateY(0);
  box-shadow: var(--shadow-industrial-sm);
}

/* 次要按钮 - 次要操作 */
.btn-secondary {
  background: var(--bg-raised);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  border-color: var(--border-accent);
}

/* 幽灵按钮 - 辅助操作 */
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid transparent;
}

.btn-ghost:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* 危险按钮 - 删除/停止等 */
.btn-danger {
  background: linear-gradient(135deg, var(--color-error-500), var(--color-error-600));
  color: white;
  border: 1px solid transparent;
}

.btn-danger:hover {
  background: linear-gradient(135deg, var(--color-error-600), var(--color-error-700));
  box-shadow: var(--shadow-glow-error);
}

/* 图标按钮 */
.btn-icon {
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: var(--radius-md);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

#### 3.1.2 按钮尺寸

```css
.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-body-sm);
  border-radius: var(--radius-sm);
  gap: var(--space-1);
}

.btn-md {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-body);
  border-radius: var(--radius-md);
  gap: var(--space-2);
}

.btn-lg {
  padding: var(--space-3) var(--space-6);
  font-size: var(--text-body-lg);
  border-radius: var(--radius-lg);
  gap: var(--space-2);
}
```

#### 3.1.3 按钮状态

```css
/* 禁用状态 */
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* 加载状态 */
.btn-loading {
  position: relative;
  color: transparent;
  pointer-events: none;
}

.btn-loading::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  top: 50%;
  left: 50%;
  margin: -8px 0 0 -8px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### 3.2 输入控件 (Input Controls)

#### 3.2.1 文本输入框

```css
.input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-body);
  font-family: var(--font-sans);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  transition: var(--transition-colors);
}

.input::placeholder {
  color: var(--text-tertiary);
}

.input:hover:not(:disabled) {
  border-color: var(--border-muted);
}

.input:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.15);
}

.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-raised);
}

/* 数值输入框 */
.input-number {
  font-family: var(--font-mono);
  text-align: right;
  letter-spacing: 0.02em;
}

/* 带图标的输入框 */
.input-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: var(--space-3);
  color: var(--text-tertiary);
  pointer-events: none;
}

.input-with-icon {
  padding-left: var(--space-10);
}
```

#### 3.2.2 下拉选择框

```css
.select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236E7681' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right var(--space-3) center;
  padding-right: var(--space-10);
  cursor: pointer;
}

.select:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.15);
}
```

#### 3.2.3 开关 (Toggle)

```css
.toggle {
  position: relative;
  width: 44px;
  height: 24px;
  background: var(--border-default);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: var(--duration-fast) var(--ease-out);
}

.toggle::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  box-shadow: var(--shadow-sm);
  transition: var(--duration-fast) var(--ease-out);
}

.toggle-active {
  background: var(--color-primary-500);
}

.toggle-active::after {
  left: 22px;
}
```

#### 3.2.4 复选框与单选框

```css
.checkbox {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-colors);
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.checkbox:checked {
  background: var(--color-primary-500);
  border-color: var(--color-primary-500);
}

.checkbox:checked::after {
  content: '';
  width: 6px;
  height: 10px;
  border: 2px solid white;
  border-top: none;
  border-left: none;
  transform: rotate(45deg) translateY(-1px);
}

.radio {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-default);
  border-radius: 50%;
  cursor: pointer;
  appearance: none;
}

.radio:checked {
  border-color: var(--color-primary-500);
}

.radio:checked::after {
  content: '';
  display: block;
  width: 10px;
  height: 10px;
  background: var(--color-primary-500);
  border-radius: 50%;
  margin: 2px;
}
```

### 3.3 卡片 (Card)

#### 3.3.1 基础卡片

```css
.card {
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: var(--transition-colors);
}

.card:hover {
  border-color: var(--border-muted);
}

.card-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: var(--text-h4);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.card-body {
  padding: var(--space-4);
}

.card-footer {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-muted);
  background: var(--bg-base);
}
```

#### 3.3.2 数据卡片 (Data Card) - 关键组件

```css
.data-card {
  background: linear-gradient(135deg, var(--bg-raised), var(--bg-overlay));
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  position: relative;
  overflow: hidden;
  transition: var(--duration-normal) var(--ease-out);
}

.data-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-primary-500), var(--color-accent-500));
}

.data-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-industrial-lg);
  border-color: var(--color-primary-500);
}

.data-card-label {
  font-size: var(--text-caption);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  margin-bottom: var(--space-2);
}

.data-card-value {
  font-size: var(--text-data);
  font-weight: var(--font-bold);
  font-family: var(--font-mono);
  color: var(--text-primary);
  line-height: var(--leading-none);
}

.data-card-unit {
  font-size: var(--text-body);
  font-weight: var(--font-normal);
  color: var(--text-secondary);
  margin-left: var(--space-1);
}

.data-card-trend {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-body-sm);
  margin-top: var(--space-2);
}

.trend-up {
  color: var(--color-success-500);
}

.trend-down {
  color: var(--color-error-500);
}

.trend-neutral {
  color: var(--text-secondary);
}

/* 状态指示器 */
.data-card-status {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-online {
  background: var(--color-success-500);
  box-shadow: var(--glow-success);
}

.status-offline {
  background: var(--color-error-500);
  box-shadow: var(--glow-error);
}

.status-warning {
  background: var(--color-warning-500);
  box-shadow: var(--glow-warning);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### 3.4 仪表盘 (Gauge)

#### 3.4.1 圆形仪表盘

```css
.gauge {
  position: relative;
  width: 180px;
  height: 180px;
}

.gauge-ring {
  transform: rotate(-90deg);
}

.gauge-bg {
  fill: none;
  stroke: var(--border-default);
  stroke-width: 12;
}

.gauge-fill {
  fill: none;
  stroke: url(#gauge-gradient);
  stroke-width: 12;
  stroke-linecap: round;
  stroke-dasharray: 283;
  stroke-dashoffset: 283;
  transition: stroke-dashoffset var(--duration-slow) var(--ease-out);
}

.gauge-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.gauge-number {
  font-size: var(--text-data-lg);
  font-weight: var(--font-bold);
  font-family: var(--font-mono);
  color: var(--text-primary);
  line-height: var(--leading-none);
}

.gauge-label {
  font-size: var(--text-caption);
  color: var(--text-secondary);
  margin-top: var(--space-1);
}

.gauge-range {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--text-caption);
  color: var(--text-tertiary);
  display: flex;
  justify-content: space-between;
  width: 100%;
}

/* 仪表盘颜色状态 */
.gauge-normal .gauge-fill { stroke: var(--color-success-500); }
.gauge-warning .gauge-fill { stroke: var(--color-warning-500); }
.gauge-danger .gauge-fill  { stroke: var(--color-error-500); }
```

#### 3.4.2 线性仪表条

```css
.progress-bar {
  height: 8px;
  background: var(--border-default);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-500), var(--color-accent-500));
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out);
}

.progress-fill.warning {
  background: linear-gradient(90deg, var(--color-warning-400), var(--color-warning-500));
}

.progress-fill.danger {
  background: linear-gradient(90deg, var(--color-error-400), var(--color-error-500));
}
```

### 3.5 数据表格 (Data Table)

#### 3.5.1 表格样式

```css
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-body-sm);
}

.data-table th {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-weight: var(--font-semibold);
  font-size: var(--text-caption);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-default);
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-muted);
  color: var(--text-primary);
  vertical-align: middle;
}

.data-table tr:hover td {
  background: var(--bg-hover);
}

.data-table .mono {
  font-family: var(--font-mono);
  font-size: var(--text-body-sm);
}

/* 寄存器表格专用 */
.register-table .address {
  font-family: var(--font-mono);
  color: var(--color-primary-400);
  font-weight: var(--font-medium);
}

.register-table .value {
  font-family: var(--font-mono);
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.register-table .status-ok {
  color: var(--color-success-500);
}

.register-table .status-error {
  color: var(--color-error-500);
}
```

#### 3.5.2 表格功能元素

```css
/* 行选择 */
.data-table tr.selected td {
  background: rgba(33, 150, 243, 0.1);
}

/* 排序指示 */
.sort-indicator {
  display: inline-flex;
  flex-direction: column;
  margin-left: var(--space-1);
  opacity: 0.3;
}

.sort-indicator.active {
  opacity: 1;
  color: var(--color-primary-500);
}

/* 分页 */
.table-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-muted);
}

.pagination-info {
  font-size: var(--text-body-sm);
  color: var(--text-secondary);
}

.pagination-controls {
  display: flex;
  gap: var(--space-1);
}
```

### 3.6 状态徽章 (Status Badge)

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-0.5) var(--space-2);
  font-size: var(--text-caption);
  font-weight: var(--font-medium);
  border-radius: var(--radius-badge);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.badge-success {
  background: rgba(76, 175, 80, 0.15);
  color: var(--color-success-500);
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.badge-warning {
  background: rgba(255, 193, 7, 0.15);
  color: var(--color-warning-500);
  border: 1px solid rgba(255, 193, 7, 0.3);
}

.badge-error {
  background: rgba(244, 67, 54, 0.15);
  color: var(--color-error-500);
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.badge-info {
  background: rgba(33, 150, 243, 0.15);
  color: var(--color-info-500);
  border: 1px solid rgba(33, 150, 243, 0.3);
}

.badge-neutral {
  background: var(--bg-overlay);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

/* 状态点 */
.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.badge-dot.pulse {
  animation: badge-pulse 1.5s infinite;
}

@keyframes badge-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.7; }
}
```

### 3.7 导航组件

#### 3.7.1 侧边导航栏

```css
.sidebar {
  width: 260px;
  background: var(--bg-base);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
}

.sidebar-header {
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-muted);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.sidebar-logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-accent-500));
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.sidebar-logo-text {
  font-size: var(--text-h4);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) 0;
}

.nav-section {
  margin-bottom: var(--space-4);
}

.nav-section-title {
  padding: var(--space-2) var(--space-5);
  font-size: var(--text-caption);
  font-weight: var(--font-semibold);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-5);
  color: var(--text-secondary);
  text-decoration: none;
  transition: var(--transition-colors);
  cursor: pointer;
}

.nav-item:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.nav-item.active {
  color: var(--color-primary-500);
  background: rgba(33, 150, 243, 0.1);
  border-right: 3px solid var(--color-primary-500);
}

.nav-item-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-item-badge {
  margin-left: auto;
  background: var(--color-error-500);
  color: white;
  font-size: var(--text-caption);
  font-weight: var(--font-semibold);
  padding: var(--space-0.5) var(--space-2);
  border-radius: var(--radius-full);
  min-width: 20px;
  text-align: center;
}
```

#### 3.7.2 设备树形列表

```css
.device-tree {
  padding: var(--space-2);
}

.device-group {
  margin-bottom: var(--space-2);
}

.device-group-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  color: var(--text-secondary);
  font-size: var(--text-body-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  border-radius: var(--radius-md);
}

.device-group-header:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.device-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2) var(--space-2) var(--space-8);
  color: var(--text-primary);
  font-size: var(--text-body-sm);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: var(--transition-colors);
}

.device-item:hover {
  background: var(--bg-hover);
}

.device-item.selected {
  background: rgba(33, 150, 243, 0.1);
  color: var(--color-primary-500);
}

.device-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
```

### 3.8 图表组件

#### 3.8.1 实时趋势图

```css
.trend-chart {
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-muted);
}

.chart-title {
  font-size: var(--text-body);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.chart-controls {
  display: flex;
  gap: var(--space-2);
}

.chart-body {
  padding: var(--space-4);
  height: 250px;
  position: relative;
}

.chart-canvas {
  width: 100%;
  height: 100%;
}

/* 图表图例 */
.chart-legend {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-muted);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-caption);
  color: var(--text-secondary);
}

.legend-color {
  width: 12px;
  height: 3px;
  border-radius: 2px;
}
```

### 3.9 弹窗与模态框

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn var(--duration-fast) var(--ease-out);
}

.modal {
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  max-width: 90vw;
  max-height: 90vh;
  overflow: hidden;
  animation: slideUp var(--duration-normal) var(--ease-out);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-muted);
}

.modal-title {
  font-size: var(--text-h3);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.modal-close {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-colors);
}

.modal-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--space-5);
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border-muted);
  background: var(--bg-base);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to { 
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
```

### 3.10 提示与通知

#### 3.10.1 Toast 通知

```css
.toast-container {
  position: fixed;
  top: var(--space-4);
  right: var(--space-4);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-overlay);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 300px;
  max-width: 400px;
  animation: toastSlide var(--duration-normal) var(--ease-out);
}

.toast-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.toast-success .toast-icon { color: var(--color-success-500); }
.toast-error .toast-icon { color: var(--color-error-500); }
.toast-warning .toast-icon { color: var(--color-warning-500); }
.toast-info .toast-icon { color: var(--color-info-500); }

.toast-content {
  flex: 1;
}

.toast-title {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.toast-message {
  font-size: var(--text-body-sm);
  color: var(--text-secondary);
}

@keyframes toastSlide {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
```

#### 3.10.2 工具提示

```css
.tooltip {
  position: relative;
}

.tooltip::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  padding: var(--space-2) var(--space-3);
  background: var(--color-gray-800);
  color: white;
  font-size: var(--text-caption);
  border-radius: var(--radius-md);
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: var(--duration-fast) var(--ease-out);
  z-index: 100;
}

.tooltip:hover::after {
  opacity: 1;
  visibility: visible;
}
```

---

## 四、布局框架

### 4.1 整体布局结构

```
┌─────────────────────────────────────────────────────────────────┐
│ 顶部栏 (Header)                                    高度: 56px   │
│ [Logo] [系统标题] [面包屑]        [搜索] [通知] [用户]          │
├──────────┬──────────────────────────────────────────────────────┤
│          │                                                      │
│ 侧边栏   │  主内容区 (Main Content)                             │
│ (Sidebar)│                                                      │
│ 宽度:    │  ┌──────────────────────────────────────────────────┐│
│ 260px   │  │ 页面标题栏                                        ││
│          │  │ [标题] [操作按钮]                                ││
│ [设备    │  ├──────────────────────────────────────────────────┤│
│  树形    │  │                                                  ││
│  列表]   │  │ 内容区域                                          ││
│          │  │                                                  ││
│          │  │                                                  ││
│          │  │                                                  ││
│          │  └──────────────────────────────────────────────────┘│
│          │                                                      │
├──────────┴──────────────────────────────────────────────────────┤
│ 底部状态栏 (Status Bar)                            高度: 28px   │
│ [连接状态] [在线设备数] [最后更新时间] [版本信息]               │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 主监控界面布局

```
┌─────────────────────────────────────────────────────────────────┐
│ 设备监控 - Pump Station A                              [设置]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────┐  ┌───────────────────────┐          │
│  │   实时趋势图            │  │   关键数据总览         │          │
│  │   (面积图/折线图)      │  │   ┌────┐ ┌────┐ ┌────┐│          │
│  │                       │  │   │温度│ │压力│ │流量││          │
│  │   ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁   │  │   │25.5│ │1.2 │ │50.3││          │
│  │                       │  │   └────┘ └────┘ └────┘│          │
│  │   时间范围: [1H][6H]  │  │   ┌────┐ ┌────┐ ┌────┐│          │
│  │           [24H][ALL]  │  │   │功率│ │频率│ │效率││          │
│  └───────────────────────┘  │   │15.2│ │50.0│ │95.2││          │
│                              │   └────┘ └────┘ └────┘│          │
│  ┌───────────────────────┐  └───────────────────────┘          │
│  │   仪表盘区域          │                                      │
│  │   ┌────┐ ┌────┐ ┌────┐                                      │
│  │   │ SQ │ │ AR │ │ B  │                                      │
│  │   │ 10 │ │ 2  │ │    │    ┌───────────────────────┐          │
│  │   └────┘ └────┘ └────┘    │   Modbus寄存器表      │          │
│  └───────────────────────┘    │  ┌────┬────┬────┬────┐│          │
│                              │  │地址│功能│数值│状态││          │
│  ┌──────────────────────────┐│  ├────┼────┼────┼────┤│          │
│  │   设备操作面板          ││  │0001│ 03 │25.5│ OK ││          │
│  │   [启动] [停止] [复位]  ││  │0002│ 03 │20.3│ OK ││          │
│  │                         ││  └────┴────┴────┴────┘│          │
│  └──────────────────────────┘│  [上一页] [1/20] [下一页]│          │
│                              └───────────────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│ ● 已连接 │ 在线: 5/6 │ 最后更新: 2024-01-15 14:30:25 │ v1.2.0   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 布局网格系统

```css
/* 12列网格 */
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--gap-lg);
}

/* 常用列宽 */
.col-1  { grid-column: span 1; }
.col-2  { grid-column: span 2; }
.col-3  { grid-column: span 3; }
.col-4  { grid-column: span 4; }
.col-6  { grid-column: span 6; }
.col-8  { grid-column: span 8; }
.col-12 { grid-column: span 12; }

/* 响应式断点 */
@media (max-width: 1200px) {
  .col-lg-3 { grid-column: span 3; }
  .col-lg-6 { grid-column: span 6; }
}

@media (max-width: 992px) {
  .col-md-4 { grid-column: span 4; }
  .col-md-6 { grid-column: span 6; }
  .col-md-12 { grid-column: span 12; }
}

@media (max-width: 768px) {
  .col-sm-12 { grid-column: span 12; }
}
```

### 4.4 响应式设计

```css
/* 桌面端 (≥1200px) */
.main-content {
  margin-left: 260px;
  padding: var(--space-6);
}

/* 平板端 (768px - 1199px) */
@media (max-width: 1199px) {
  .sidebar {
    width: 72px;
  }
  
  .sidebar-logo-text,
  .nav-item-text,
  .nav-section-title {
    display: none;
  }
  
  .main-content {
    margin-left: 72px;
  }
}

/* 移动端 (<768px) */
@media (max-width: 767px) {
  .sidebar {
    transform: translateX(-100%);
    width: 260px;
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
  
  .main-content {
    margin-left: 0;
    padding: var(--space-4);
  }
  
  .data-card {
    grid-column: span 12;
  }
}
```

---

## 五、深色主题完整方案

### 5.1 主题变量定义

```css
/* ===========================
   深色主题 (Dark Theme)
   =========================== */

:root {
  /* 背景色 - 由浅到深 */
  --bg-primary: #0F1419;      /* 主背景 - 最深 */
  --bg-secondary: #161B22;    /* 卡片/面板背景 */
  --bg-tertiary: #1C2128;     /* 弹窗/下拉背景 */
  --bg-hover: #21262D;        /* 悬停态 */
  --bg-active: #30363D;       /* 激活态 */
  
  /* 文本色 - 由深到浅 */
  --text-primary: #E6EDF3;    /* 主要文本 - 最亮 */
  --text-secondary: #8B949E; /* 次要文本 */
  --text-tertiary: #6E7681;   /* 禁用/提示文本 */
  --text-inverse: #0D1117;    /* 深色背景上的浅色文本 */
  
  /* 边框色 */
  --border-default: #30363D;  /* 默认边框 */
  --border-muted: #21262D;   /* 弱边框 */
  --border-accent: #388BFD;   /* 强调边框 (聚焦态) */
  
  /* 交互效果 */
  --shadow-color: rgba(0, 0, 0, 0.4);
  --overlay-color: rgba(0, 0, 0, 0.6);
  
  /* 组件背景 */
  --input-bg: #0D1117;
  --card-bg: #161B22;
  --modal-bg: #1C2128;
  --dropdown-bg: #1C2128;
  
  /* 状态指示 */
  --status-online: #3FB950;
  --status-offline: #F85149;
  --status-warning: #D29922;
}

/* ===========================
   浅色主题 (Light Theme)
   =========================== */

[data-theme="light"] {
  /* 背景色 - 由浅到深 */
  --bg-primary: #FFFFFF;
  --bg-secondary: #F6F8FA;
  --bg-tertiary: #FFFFFF;
  --bg-hover: #F3F4F6;
  --bg-active: #E5E7EB;
  
  /* 文本色 - 由浅到深 */
  --text-primary: #1F2937;
  --text-secondary: #6B7280;
  --text-tertiary: #9CA3AF;
  --text-inverse: #FFFFFF;
  
  /* 边框色 */
  --border-default: #D1D5DB;
  --border-muted: #E5E7EB;
  --border-accent: #2563EB;
  
  /* 交互效果 */
  --shadow-color: rgba(0, 0, 0, 0.1);
  --overlay-color: rgba(0, 0, 0, 0.4);
  
  /* 组件背景 */
  --input-bg: #FFFFFF;
  --card-bg: #FFFFFF;
  --modal-bg: #FFFFFF;
  --dropdown-bg: #FFFFFF;
}
```

### 5.2 深色主题专用组件样式

```css
/* 输入框 - 深色主题 */
[data-theme="dark"] .input {
  background: var(--input-bg);
  border-color: var(--border-default);
  color: var(--text-primary);
}

[data-theme="dark"] .input::placeholder {
  color: var(--text-tertiary);
}

[data-theme="dark"] .input:focus {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.25);
}

/* 卡片 - 深色主题 */
[data-theme="dark"] .card {
  background: var(--card-bg);
  border-color: var(--border-default);
}

[data-theme="dark"] .card:hover {
  border-color: var(--border-accent);
}

/* 表格 - 深色主题 */
[data-theme="dark"] .data-table th {
  background: var(--bg-primary);
  color: var(--text-secondary);
}

[data-theme="dark"] .data-table td {
  border-color: var(--border-muted);
}

[data-theme="dark"] .data-table tr:hover td {
  background: var(--bg-hover);
}

/* 模态框 - 深色主题 */
[data-theme="dark"] .modal {
  background: var(--modal-bg);
  border-color: var(--border-default);
}

/* 仪表盘发光效果 - 深色主题 */
[data-theme="dark"] .gauge-ring {
  filter: drop-shadow(0 0 8px rgba(33, 150, 243, 0.3));
}

[data-theme="dark"] .data-card::before {
  box-shadow: 0 0 20px rgba(33, 150, 243, 0.3);
}
```

### 5.3 主题切换动效

```css
/* 主题切换过渡 */
body {
  transition: 
    background-color var(--duration-normal) var(--ease-out),
    color var(--duration-normal) var(--ease-out);
}

/* 主题切换按钮 */
.theme-toggle {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: var(--transition-colors);
}

.theme-toggle:hover {
  background: var(--bg-hover);
  border-color: var(--border-accent);
}

.theme-toggle-icon {
  width: 20px;
  height: 20px;
  color: var(--text-secondary);
  transition: var(--duration-normal) var(--ease-out);
}

.theme-toggle-icon.sun {
  display: none;
}

.theme-toggle-icon.moon {
  display: block;
}

[data-theme="light"] .theme-toggle-icon.sun {
  display: block;
}

[data-theme="light"] .theme-toggle-icon.moon {
  display: none;
}
```

---

## 六、交互规范

### 6.1 微交互设计

#### 6.1.1 按钮交互

```css
/* 按钮点击涟漪效果 */
.btn {
  position: relative;
  overflow: hidden;
}

.btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: width 0.4s ease, height 0.4s ease;
}

.btn:active::after {
  width: 200px;
  height: 200px;
}
```

#### 6.1.2 卡片悬浮效果

```css
.data-card {
  transform: translateY(0);
  transition: 
    transform var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out),
    border-color var(--duration-normal) var(--ease-out);
}

.data-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-industrial-lg);
}

/* 卡片内容动画 */
.data-card:hover .data-card-value {
  color: var(--color-primary-400);
}
```

#### 6.1.3 数值变化动画

```css
/* 数值变化时闪烁效果 */
.value-changing {
  animation: valueFlash 0.5s ease;
}

@keyframes valueFlash {
  0% { color: var(--text-primary); }
  50% { color: var(--color-primary-400); background: rgba(33, 150, 243, 0.1); }
  100% { color: var(--text-primary); }
}

/* 数值增加 */
.value-increase {
  animation: valueIncrease 0.3s ease;
}

@keyframes valueIncrease {
  0% { color: var(--text-primary); }
  100% { color: var(--color-success-500); }
}

/* 数值减少 */
.value-decrease {
  animation: valueDecrease 0.3s ease;
}

@keyframes valueDecrease {
  0% { color: var(--text-primary); }
  100% { color: var(--color-error-500); }
}
```

### 6.2 加载状态

#### 6.2.1 骨架屏

```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-secondary) 25%,
    var(--bg-hover) 50%,
    var(--bg-secondary) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
  border-radius: var(--radius-md);
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-text {
  height: 14px;
  margin-bottom: var(--space-2);
}

.skeleton-title {
  height: 20px;
  width: 60%;
  margin-bottom: var(--space-3);
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.skeleton-chart {
  height: 200px;
  width: 100%;
}
```

#### 6.2.2 数据加载指示

```css
/* 表格加载态 */
.table-loading {
  position: relative;
  min-height: 200px;
}

.table-loading::after {
  content: '加载中...';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--text-secondary);
  font-size: var(--text-body);
}

/* 图表加载态 */
.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
}

.chart-loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-default);
  border-top-color: var(--color-primary-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
```

### 6.3 空状态设计

```css
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-6);
  text-align: center;
}

.empty-state-icon {
  width: 64px;
  height: 64px;
  color: var(--text-tertiary);
  margin-bottom: var(--space-4);
}

.empty-state-title {
  font-size: var(--text-h3);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.empty-state-description {
  font-size: var(--text-body);
  color: var(--text-secondary);
  max-width: 360px;
  margin-bottom: var(--space-6);
}
```

### 6.4 错误状态设计

```css
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-8);
  text-align: center;
}

.error-state-icon {
  width: 48px;
  height: 48px;
  color: var(--color-error-500);
  margin-bottom: var(--space-4);
}

.error-state-title {
  font-size: var(--text-h3);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.error-state-message {
  font-size: var(--text-body);
  color: var(--text-secondary);
  margin-bottom: var(--space-4);
  font-family: var(--font-mono);
  background: var(--bg-base);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  max-width: 100%;
  overflow-x: auto;
}

.error-state-actions {
  display: flex;
  gap: var(--space-3);
}
```

---

## 七、可访问性设计

### 7.1 焦点管理

```css
/* 焦点样式 */
:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

/* 键盘导航焦点 */
:focus:not(:focus-visible) {
  outline: none;
}

/* 跳过链接 */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--color-primary-500);
  color: white;
  padding: var(--space-2) var(--space-4);
  z-index: 10000;
  transition: top var(--duration-fast);
}

.skip-link:focus {
  top: 0;
}
```

### 7.2 ARIA 标签

```html
<!-- 按钮 -->
<button class="btn" aria-label="连接设备">
  <svg aria-hidden="true"><!-- 图标 --></svg>
</button>

<!-- 输入框 -->
<input 
  type="text" 
  class="input"
  aria-label="设备名称"
  aria-describedby="device-name-help"
/>
<span id="device-name-help" class="sr-only">请输入设备的名称</span>

<!-- 数据卡片 -->
<div class="data-card" role="region" aria-label="温度监控数据">
  <span class="data-card-label">温度</span>
  <span class="data-card-value" aria-live="polite">25.5°C</span>
</div>

<!-- 状态徽章 -->
<span class="badge badge-success" role="status" aria-label="设备状态: 在线">
  <span aria-hidden="true">●</span> 在线
</span>
```

### 7.3 减少动画偏好

```css
/* 尊重用户减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  
  .skeleton {
    animation: none;
    background: var(--bg-secondary);
  }
}

/* 系统级设置 */
[data-reduced-motion="true"] * {
  animation-duration: 0.01ms !important;
  transition-duration: 0.01ms !important;
}
```

---

## 八、图标系统

### 8.1 图标设计规范

```css
/* 图标尺寸 */
.icon-xs  { width: 12px; height: 12px; }
.icon-sm  { width: 16px; height: 16px; }
.icon-md  { width: 20px; height: 20px; }
.icon-lg  { width: 24px; height: 24px; }
.icon-xl  { width: 32px; height: 32px; }
.icon-2xl { width: 48px; height: 48px; }

/* 图标颜色继承 */
.icon {
  width: var(--icon-md);
  height: var(--icon-md);
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}
```

### 8.2 推荐图标库

- **Phosphor Icons** - 现代、一致性好
- **Lucide** - 开源、简洁
- **Heroicons** - Tailwind官方

---

## 九、附录：完整样式变量清单

```css
:root {
  /* ====================
     颜色
     ==================== */
  
  /* 主色 */
  --color-primary-50:  #E3F2FD;
  --color-primary-100: #BBDEFB;
  --color-primary-200: #90CAF9;
  --color-primary-300: #64B5F6;
  --color-primary-400: #42A5F5;
  --color-primary-500: #2196F3;
  --color-primary-600: #1E88E5;
  --color-primary-700: #1976D2;
  --color-primary-800: #1565C0;
  --color-primary-900: #0D47A1;
  
  /* 功能色 */
  --color-success-500: #4CAF50;
  --color-warning-500: #FFC107;
  --color-error-500:   #F44336;
  --color-info-500:    #2196F3;
  
  /* ====================
     字体
     ==================== */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  
  /* ====================
     字号
     ==================== */
  --text-display: 2.5rem;
  --text-h1: 2rem;
  --text-h2: 1.5rem;
  --text-h3: 1.25rem;
  --text-h4: 1.125rem;
  --text-body-lg: 1rem;
  --text-body: 0.9375rem;
  --text-body-sm: 0.875rem;
  --text-caption: 0.8125rem;
  --text-data-lg: 2rem;
  --text-data: 1.5rem;
  
  /* ====================
     间距
     ==================== */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-10: 2.5rem;
  --space-12: 3rem;
  --space-16: 4rem;
  
  /* ====================
     圆角
     ==================== */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-2xl: 1rem;
  --radius-full: 9999px;
  
  /* ====================
     阴影
     ==================== */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.15);
  
  /* ====================
     动画
     ==================== */
  --duration-instant: 50ms;
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 400ms;
  --duration-slower: 600ms;
  
  --ease-linear: linear;
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
}
```

---

## 十、WPF 实现建议

### 10.1 资源字典结构

```
Resources/
├── Themes/
│   ├── Colors.xaml          # 颜色资源
│   ├── Typography.xaml      # 字体样式
│   ├── Buttons.xaml         # 按钮样式
│   ├── Inputs.xaml          # 输入控件样式
│   ├── Cards.xaml           # 卡片样式
│   ├── DataTable.xaml       # 表格样式
│   ├── Navigation.xaml      # 导航样式
│   └── Animations.xaml      # 动画定义
├── Templates/
│   ├── ButtonTemplate.xaml
│   ├── CardTemplate.xaml
│   └── GaugeTemplate.xaml
└── Styles/
    └── GlobalStyles.xaml
```

### 10.2 建议使用的 WPF 技术

- **ResourceDictionary** - 组织主题资源
- **Style.TargetType** - 统一控件样式
- **VisualStateManager** - 管理控件状态
- **Storyboard** - 定义动画效果
- **DataTemplate** - 数据绑定模板
- **Custom Control** - 自定义仪表盘等复杂组件

---

**设计方案版本**: v1.0  
**更新日期**: 2024年1月  
**状态**: 待实施
