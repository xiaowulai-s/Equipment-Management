# GitHub 上传指南

## 版本信息
- **当前版本**: v1.1.0
- **发布日期**: 2026-03-24
- **提交哈希**: 请查看最新的 commit

## 上传步骤

### 1. 创建 GitHub 仓库

在 GitHub 上创建新仓库：
- 仓库名称：`equipment-management` 或 `industrial-equipment-monitor`
- 可见性：Public 或 Private
- 初始化：不要添加 README、.gitignore 或 license（我们已经有了）

### 2. 关联远程仓库

```bash
cd "e:\下载\app\equipment management"

# 添加远程仓库（替换为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/equipment-management.git

# 验证远程仓库
git remote -v
```

### 3. 上传代码

```bash
# 推送到 GitHub
git push -u origin main

# 如果是 master 分支
git push -u origin master
```

### 4. 创建版本标签

```bash
# 创建 v1.1.0 标签
git tag -a v1.1.0 -m "Release version 1.1.0"

# 推送标签
git push origin v1.1.0
```

### 5. 在 GitHub 上创建 Release

1. 访问 GitHub 仓库
2. 点击 "Releases" → "Draft a new release"
3. 选择标签 `v1.1.0`
4. 填写发布说明（使用 CHANGELOG.md 内容）
5. 点击 "Publish release"

## 发布说明模板

```markdown
## 工业设备管理系统 v1.1.0

### 新功能

#### 1. 报警系统
- 多级报警（INFO、WARNING、ERROR、CRITICAL）
- 阈值报警（高温、高压等）
- 可视化报警规则配置界面

#### 2. 数据导出
- 支持 CSV/Excel/JSON 格式
- 报警历史导出

#### 3. 批量操作
- 批量连接/断开/删除设备
- 设备选择界面

#### 4. 寄存器配置
- 多寄存器地址配置
- 快速添加常用寄存器

### 界面优化
- 工业级 UI 规范
- 统一按钮风格
- 表格样式优化

### 技术栈
- Python 3.8+
- PySide6 6.5+

### 安装使用

```bash
pip install -r requirements.txt
python main.py
```

详细文档请查看 [README.md](README.md)
```

## 常见问题

### 问题 1: 推送失败

如果遇到认证失败：
```bash
# 使用 token 认证
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/equipment-management.git
git push -u origin main
```

### 问题 2: 分支名称

如果默认分支是 master 而不是 main：
```bash
git branch -M master
git push -u origin master
```

### 问题 3: 大文件

如果有大文件被拒绝：
```bash
# 安装 git-lfs
git lfs install

# 跟踪大文件
git lfs track "*.png"
git lfs track "*.jpg"

# 重新添加
git add .gitattributes
git commit -m "Add LFS tracking"
```

## 后续维护

### 发布新版本

1. 更新版本号（main.py）
2. 更新 CHANGELOG.md
3. 提交代码
4. 创建 git tag
5. 推送到 GitHub

```bash
git commit -am "feat: 发布 v1.2.0 版本"
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

## 仓库链接

- GitHub: `https://github.com/YOUR_USERNAME/equipment-management.git`
- 替换 `YOUR_USERNAME` 为你的 GitHub 用户名

## 许可证

建议使用 MIT 许可证，已在项目根目录创建 LICENSE 文件。
