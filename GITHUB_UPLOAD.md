# GitHub 上传指南

> **项目名称**: 工业设备管理系统 (Equipment Management System)
> **版本**: v1.5.1
> **更新日期**: 2026-03-29

---

## 📋 目录

### 1. [准备阶段](#1-准备阶段)
### 2. [初始化仓库](#2-初始化仓库)
### 3. [上传文件](#3-上传文件)
### 4. [创建发布](#4-创建发布)
### 5. [验证和发布](#5-验证和发布)

---

## 1. 准备阶段

### 1.1 检查项目文件

#### 核心文件清单
```
✅ README.md - 项目说明
✅ CHANGELOG.md - 更新日志
✅ LICENSE - MIT 许可证
✅ requirements.txt - Python 依赖
✅ .gitignore - Git 忽略文件
```

#### 重要代码文件
```
✅ main_v2.py - 主程序入口
✅ core/ - 核心模块
├── version.py - 版本信息
├── device/ - 设备管理
├── communication/ - 通信驱动
├── protocols/ - 协议层
├── data/ - 数据层
├── utils/ - 工具模块
```

#### UI 文件
```
✅ ui/ - UI 层
├── main_window_v2.py - 主窗口
├── dialogs/ - 对话框
├── widgets/ - 组件
└── styles.py - 样式定义
```

#### 文档文件
```
✅ Python UI 组件库完整方案.md - 组件库文档
✅ AI组件使用提示词.md - AI 提示词
✅ 项目进度.md - 项目进度
✅ 新架构说明.md - 架构说明
```

### 1.2 检查项目配置

#### 版本号确认
```python
# core/version.py
__version__ = "1.3.0"
```

#### README 更新
- ✅ 版本号已更新为 v1.3.0
- ✅ 特性列表完整
- ✅ 架构图清晰
- ✅ 安装说明完整
- ✅ 截图链接完整

#### CHANGELOG 更新
- ✅ v1.3.0 变更日志已添加
- ✅ 详细记录所有新功能
- ✅ 详细记录所有优化
- ✅ 详细记录所有修复

### 1.3 检查敏感信息

#### 敏感文件过滤
```
✅ data/*.db - 数据库文件
✅ config/*.json - 配置文件
✅ *.log - 日志文件
✅ *.pyc - Python 编译文件
✅ *.pyo - Python 优化文件
```

#### IDE 文件过滤
```
✅ .idea/ - PyCharm
✅ .vscode/ - VS Code
✅ *.pyc - 编译缓存
✅ __pycache__/ - Python 缓存
✅ .pytest_cache/ - 测试缓存
```

---

## 2. 初始化仓库

### 2.1 创建 GitHub 仓库

#### 步骤
1. 访问 [GitHub](https://github.com/) 并登录
2. 点击右上角 "+" 号，选择 "New repository"
3. 填写仓库信息：
   - Repository name: `Equipment-Management`
   - Description: `基于 PySide6 和 Modbus 协议的工业设备上位机监控软件，采用四层解耦架构，支持多设备并发管理和实时数据可视化。`
   - Public: ✅ 勾选公开
   - Initialize with: README
   - .gitignore: 选择 "Add a .gitignore file"
4. 点击 "Create repository"

### 2.2 获取仓库地址

```
仓库 URL: https://github.com/xiaowulai-s/Equipment-Management.git
或
git remote add origin https://github.com/xiaowulai-s/Equipment-Management.git
```

### 2.3 初始化本地仓库（如果已创建）

```bash
# 在项目根目录执行
cd "e:\下载\app\equipment management"

# 初始化 Git 仓库
git init

# 添加远程仓库
git remote add origin https://github.com/xiaowulai-s/Equipment-Management.git

# 重命名分支（如果需要）
git branch -M main
```

---

## 3. 上传文件

### 3.1 添加所有文件

```bash
# 添加所有文件到暂存区
git add .

# 检查暂存状态
git status
```

### 3.2 创建初始提交

```bash
# 创建初始提交
git commit -m "Initial commit - v1.3.0

- 工业设备管理系统 v1.3.0

新增功能：
- UI 组件库系统（23个可复用组件）
- 高级可视化组件（ModernGauge, AnimatedStatusBadge, RealtimeChart）
- 中文本地化完成
- AI 辅助系统（完整提示词文档）

优化和修复：
- 样式系统统一（浅色主题为默认）
- 文档完善（CHANGELOG, README, 组件库文档）
- 版本管理更新
```

### 3.3 推送到远程仓库

```bash
# 推送到 main 分支
git push -u origin main

# 如果是首次推送，使用：
git push -u origin master
```

### 3.4 验证上传

#### 验证步骤
1. 访问仓库主页
2. 检查 README.md 是否正确显示
3. 检查文件结构是否完整
4. 检查 CHANGELOG.md 是否正确显示

---

## 4. 创建发布

### 4.1 创建 Release

#### 方法 1：通过网页创建
1. 访问仓库页面：https://github.com/xiaowulai-s/Equipment-Management
2. 点击右侧 "Releases" 标签
3. 点击 "Create a new release"
4. 填写发布信息：
   - Tag version: `v1.3.0`
   - Release title: `v1.3.0 - 组件库和AI辅助版本`
   - Description:
     ```
     工业设备管理系统 v1.3.0 发布

     主要新功能：
     - UI 组件库系统（23个可复用组件）
     - 高级可视化组件（ModernGauge, AnimatedStatusBadge, RealtimeChart）
     - 中文本地化完成
     - AI 辅助系统（完整提示词文档）

     优化和修复：
     - 样式系统统一（浅色主题为默认）
     - 文档完善（CHANGELOG, README, 组件库文档）
     - 版本管理更新

     技术栈：
     - Python 3.8+
     - PySide6 6.5+
     ```
   - Target: `main`
   - 发布为预发布：✅ 勾选
5. 点击 "Publish release"

#### 方法 2：通过命令行创建（推荐）

```bash
# 使用 GitHub CLI 创建发布
gh release create v1.3.0 \
  --title "v1.3.0 - 组件库和AI辅助版本" \
  --notes "工业设备管理系统 v1.3.0 发布

主要新功能：
- UI 组件库系统（23个可复用组件）
- 高级可视化组件（ModernGauge, AnimatedStatusBadge, RealtimeChart）
- 中文本地化完成
- AI 辅助系统（完整提示词文档）

优化和修复：
- 样式系统统一（浅色主题为默认）
- 文档完善（CHANGELOG, README, 组件库文档）
- 版本管理更新

技术栈：
- Python 3.8+
- PySide6 6.5+"
```

### 4.2 添加 Release Assets（可选）

#### 添加说明
如果需要发布独立的安装包或可执行文件，可以添加附件。

#### 附件类型
- 源码压缩包（.zip / .tar.gz）
- Windows 可执行文件（.exe）
- macOS 可执行文件（.dmg / .app）
- 安装说明文档

---

## 5. 验证和发布

### 5.1 验证 Release

#### 验证清单
- [ ] Release 标签正确显示为 v1.3.0
- [ ] Release 说明完整清晰
- [ ] 源码压缩包可下载
- [ ] 版本号在 README 中更新
- [ ] 版本号在 CHANGELOG 中记录
- [ ] License 文件包含在仓库中

### 5.2 测试安装

#### 测试步骤
1. 克隆仓库到新目录：
   ```bash
   git clone https://github.com/xiaowulai-s/Equipment-Management.git
   cd Equipment-Management
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 运行程序：
   ```bash
   python main_v2.py
   ```

4. 验证功能：
   - UI 是否正常显示
   - 设备管理功能是否正常
   - 主题切换是否正常
   - 文档链接是否正确

### 5.3 发布通知

#### 通知渠道
- GitHub Release 页面
- 项目 README 添加发布公告
- 社交媒体或社区论坛

#### 通知模板
```
🎉 工业设备管理系统 v1.3.0 已发布！

主要新功能：
✅ UI 组件库系统（23个可复用组件）
✅ 高级可视化组件（ModernGauge, AnimatedStatusBadge, RealtimeChart）
✅ 中文本地化完成
✅ AI 辅助系统（完整提示词文档）

📍 下载地址：
- GitHub: https://github.com/xiaowulai-s/Equipment-Management/releases/tag/v1.3.0
```

---

## 📝 常见问题

### Q: 上传失败怎么办？

**A:**
1. 检查网络连接
2. 检查仓库权限
3. 检查 .gitignore 配置
4. 使用 `git push -v` 查看详细信息

### Q: 文件太大怎么办？

**A:**
1. GitHub 单个文件限制为 100MB
2. 使用 Git LFS (Large File Storage)
3. 压缩大型文件
4. 删除不必要的文件

### Q: 如何删除已上传的文件？

**A:**
```bash
# 删除文件
git rm --cached filename

# 提交删除
git commit -m "Remove unnecessary file"

# 推送到远程
git push
```

### Q: 如何修改已提交的文件？

**A:**
```bash
# 修改文件
# （编辑文件内容）

# 查看状态
git status

# 添加修改
git add filename

# 提交修改
git commit -m "Update feature"

# 推送
git push
```

### Q: 如何合并分支？

**A:**
```bash
# 切换到 main 分支
git checkout main

# 拉取其他分支
git pull origin feature-branch

# 合并
git merge feature-branch

# 推送
git push origin main
```

---

## 🔗 相关资源

### 官方文档
- [Git 基础](https://git-scm.com/docs/gith)
- [GitHub CLI 文档](https://cli.github.com/manual/)
- [Git 忽略文件](https://git-scm.com/docs/gitignore)

### 项目资源
- [README.md](./README.md)
- [CHANGELOG.md](./CHANGELOG.md)
- [Python UI 组件库完整方案.md](./Python%20UI%20组件库完整方案.md)
- [AI组件使用提示词.md](./AI组件使用提示词.md)

---

**文档版本**: v1.0.0
**最后更新**: 2026-03-26
**维护者**: 开发团队
