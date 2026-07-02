# Baseline 复现运行手册

> 基于 `openai/openai-cs-agents-demo` (MIT License) 的基础复现版本。

---

## 1. 环境要求

| 组件 | 版本要求 | 已验证版本 |
|------|---------|-----------|
| Python | ≥ 3.10 | 3.13.5 |
| Node.js | ≥ 18 | v24.15.0 |
| npm | ≥ 9 | 11.12.1 |
| 操作系统 | macOS / Linux / Windows | Windows 11 |

### 关键依赖版本

| 包 | 版本 | 说明 |
|---|---|---|
| `openai-agents` | 0.17.7 | Agent 编排 SDK |
| `openai-chatkit` | 1.6.5 | ChatKit 服务端 |
| `next` | 15.5.7 | Next.js 前端框架 |
| `@openai/chatkit-react` | 1.3.x | ChatKit React 组件 |

---

## 2. 快速启动

### 2.1 环境变量

```bash
# 方式 1：设置环境变量
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 方式 2：复制 .env.example 并填写
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 2.2 Python 后端

```bash
cd python-backend

# 创建虚拟环境（首次）
python -m venv .venv

# 激活虚拟环境
# Linux/macOS:
source .venv/bin/activate
# Windows (Git Bash):
source .venv/Scripts/activate

# 安装依赖（首次）
pip install -r requirements.txt

# 启动后端
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端启动后访问：**http://localhost:8000**

- `/health` — 健康检查
- `/chatkit/bootstrap` — ChatKit 初始化快照
- `/docs` — 自动生成的 OpenAPI 文档

### 2.3 Next.js 前端

```bash
cd ui

# 安装依赖（首次）
npm install

# 开发模式启动
npm run dev

# 或仅启动前端（需要后端已单独启动）
npm run dev:next
```

前端启动后访问：**http://localhost:3000**

### 2.4 同时启动前后端

```bash
cd ui
npm run dev
```

此命令通过 `concurrently` 同时启动前端和后端。

---

## 3. 验证流程

### 3.1 健康检查

```bash
curl http://localhost:8000/health
# 返回: {"status":"healthy"}
```

### 3.2 完整客服对话测试（航旅场景）

在浏览器中打开 http://localhost:3000 ，尝试以下对话：

**Demo 1：座位变更**

1. 输入："Can I change my seat?"
2. 观察 Triage Agent → Seat & Special Services Agent
3. 继续："What's the status of my flight?"
4. 观察 Handoff 到 Flight Information Agent

**Demo 2：航班取消 + Guardrail**

1. 输入："I want to cancel my flight"
2. Triage → Booking & Cancellation Agent
3. 输入："That's correct" 确认取消
4. 输入："Write a poem about strawberries"
5. 观察 Relevance Guardrail 触发（红色）

**Demo 3：延误处理**

1. 输入："I'm flying Paris to Austin via New York and my first leg is delayed."
2. 观察完整的 Triage → Flight Info → Booking → Seat → Refunds 链条

### 3.3 运行测试

```bash
cd python-backend
source .venv/Scripts/activate  # 或 source .venv/bin/activate
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## 4. 已知问题

| 问题 | 影响 | 解决方案 |
|------|------|---------|
| Windows 不支持 `concurrently` 的 Unix shell 语法 | `npm run dev` 可能失败 | 分别启动 `dev:next` 和 `dev:server` |
| 内存存储（MemoryStore）不持久化 | 服务重启后会话丢失 | 阶段 4 替换为 SQLite |
| CORS 仅允许 `localhost:3000` | 其他来源被拒绝 | 修改 main.py 或使用环境变量 |
| Mock 数据有限（2 套行程） | 仅支持预定义对话流程 | 后续阶段扩展数据 |
| 模型调用需要 API Key | 无 Key 时任何 Agent 对话均失败 | 确保 `OPENAI_API_KEY` 已设置 |
| GRPC/grpcio 未安装 | 某些 Agent SDK 特性可能不可用 | 非必需，不影响基础功能 |

---

## 5. 兼容性修复记录

| 修复 | 原因 | 日期 |
|------|------|------|
| `dev:server` 脚本改为 `python -m uvicorn` | 原脚本用 Unix 路径 `.venv/bin/uvicorn`，Windows 不兼容 | 2026-07-02 |
| 移除 `pnpm-lock.yaml` | 项目统一使用 npm 管理依赖 | 2026-07-02 |
| `package.json` name 改为 `commercecare-agent-ui` | 去品牌化 | 2026-07-02 |

---

## 6. 目录结构（实际）

```
commercecare-agent/
├── .env.example
├── .gitignore
├── CLAUDE.md
├── LICENSE                     # MIT License（来自上游）
├── NOTICE.md
├── README.md
├── docs/
│   ├── architecture_baseline.md
│   ├── baseline_runbook.md
│   ├── project_roadmap.md
│   └── upstream_audit.md
├── python-backend/
│   ├── main.py                 # FastAPI 入口
│   ├── server.py               # ChatKit 服务端实现
│   ├── memory_store.py         # 内存存储
│   ├── requirements.txt
│   ├── tests/
│   │   └── test_baseline.py    # 基础测试
│   └── airline/
│       ├── agents.py           # 6 Agent 定义 + Handoff 图
│       ├── context.py          # Agent 上下文模型
│       ├── guardrails.py       # Relevance + Jailbreak Guardrails
│       ├── tools.py            # 10 个 Mock 工具函数
│       └── demo_data.py        # Mock 行程数据
└── ui/
    ├── app/                    # Next.js App Router
    ├── components/             # React 组件
    ├── lib/                    # API 客户端、类型、工具函数
    ├── public/                 # 静态资源
    └── package.json
```
