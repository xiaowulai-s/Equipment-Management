# Git 提交规范

## 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

## 类型（type）

- **feat**: 新功能
- **fix**: 修复 bug
- **docs**: 文档更新
- **style**: 代码格式调整（不影响代码运行）
- **refactor**: 重构（既不是新功能也不是 bug 修复）
- **test**: 测试相关（添加或修改测试）
- **chore**: 构建过程或辅助工具变动
- **perf**: 性能优化
- **ci**: CI/CD配置更新

## 范围（scope）

用于说明 commit 影响的范围，例如：
- `core` - 核心模块
- `ui` - 界面模块
- `comm` - 通信层
- `proto` - 协议层
- `device` - 设备管理
- `alarm` - 报警系统
- `export` - 数据导出
- `logger` - 日志系统
- `config` - 配置管理

## 主题（subject）

- 用一句话清楚地描述这次提交做了什么
- 使用现在时态（"add" 而不是 "added"）
- 第一个字母小写
- 结尾不加句号
- 长度不超过 50 个字符

## 正文（body）

- 详细描述为什么做这个改动
- 说明改动的动机和解决方案
- 每行不超过 72 个字符

## 页脚（footer）

- 关联的 Issue：`Closes #123`
- 破坏性变更：`BREAKING CHANGE: <description>`

## 示例

### 新功能
```
feat(device): 添加设备类型管理功能

- 创建设备类型对话框
- 实现设备类型增删改查
- 支持设备类型描述自动生成

Closes #45
```

### Bug 修复
```
fix(comm): 修复 ModbusTCP 连接超时问题

- 增加连接超时配置
- 优化异常处理逻辑
- 添加重试机制

Fixes #32
```

### 重构
```
refactor(core): 重构设备管理器信号系统

- 统一信号命名规范
- 优化信号连接逻辑
- 添加信号文档

BREAKING CHANGE: 设备管理器信号名称变更
```

### 文档更新
```
docs: 更新 README 安装说明

- 添加 Python 版本要求
- 补充依赖安装步骤
- 添加快速开始示例
```

### 代码格式
```
style(ui): 统一按钮样式格式

- 应用 Black 格式化
- 调整导入顺序
```

## 禁止的提交

- ❌ "update"
- ❌ "fix bug"
- ❌ "temp commit"
- ❌ "asdfasdf"
- ❌ 空提交消息

## 预提交检查

提交前确保：
- [ ] 代码通过 Flake8 检查
- [ ] 代码通过 Black 格式化
- [ ] 类型提示完整
- [ ] 文档字符串完整
- [ ] 测试通过
