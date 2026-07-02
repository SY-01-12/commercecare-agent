# CommerceCare Agent

## 项目定位

基于多智能体、RAG、工具调用与人工转接的电商售后智能客服系统。

## 目标

参考 GitHub 仓库 `openai/openai-cs-agents-demo` 完成可运行的基础复现，再逐步改造成独立的 CommerceCare Agent，并同步到 GitHub。

---

## 强制开发规范

### 1. 版本管理

全程使用 Git 管理版本。

### 2. 分支保护

`main` 分支必须尽量保持可运行，不允许直接在 `main` 上开发新功能。

### 3. 分支命名

每个阶段创建独立分支，命名格式：

- `chore/...` — 构建、依赖、配置等杂项
- `feat/...` — 新功能
- `fix/...` — 缺陷修复
- `docs/...` — 文档

### 4. 修改前检查

每次修改前必须执行：

```bash
git status --short
git branch --show-current
```

### 5. 提交前验证

每次提交前必须执行：

```bash
git diff --check
```

以及与本次功能相关的测试、构建或启动验证。同时检查以下内容未被加入 Git：

- `.env` 文件
- 密钥文件
- 数据库文件
- 日志文件
- 缓存文件
- 本地向量库

### 6. 暂存规则

**不允许使用 `git add .`**。必须明确列出本次提交的文件。

### 7. 高风险操作禁令

以下操作**不允许执行**，除非用户明确确认：

- `git reset --hard`
- `git clean -fd`
- 强制推送（`git push --force`）
- 删除大量文件
- `curl | bash`、`Invoke-WebRequest | iex` 等远程脚本执行

### 8. 依赖审查

克隆或安装依赖前，先检查以下文件并说明即将执行的命令及风险：

- README
- LICENSE
- `package.json` 中的 scripts
- Python requirements / pyproject.toml
- Docker 配置
- 安装脚本

### 9. 安全红线

- 不读取、不显示、不提交任何 API Key、Token、`.env` 内容或 GitHub 凭据。

### 10. 语言规范

- 代码标识符使用英文
- 前端页面、演示数据、README 和项目说明优先使用中文

### 11. 阶段输出

每完成一个阶段，输出：

- 修改文件列表
- 当前架构说明
- 测试结果
- Git 分支、提交记录和待办事项

### 12. 提交与推送

- 不允许擅自提交或推送未验证的代码
- 验证通过后再进行 Git commit
- 需要创建 GitHub 仓库、推送分支、创建 PR 或合并 PR 时，先说明将执行的 GitHub 操作

### 13. 上游项目引用

上游项目 `openai/openai-cs-agents-demo` 仅作为参考来源。保留其 MIT 许可证和必要署名；不得将原项目直接包装为"完全原创项目"。
