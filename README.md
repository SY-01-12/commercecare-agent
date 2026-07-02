# CommerceCare Agent

基于多智能体、RAG、工具调用与人工转接的电商售后智能客服系统。

## 项目简介

CommerceCare Agent 是一个智能电商售后客服系统，采用多智能体协作架构，能够自动处理：

- 📦 **订单查询** — 订单状态、物流追踪、订单详情
- 🔄 **退换货处理** — 退款申请、退货流程、换货协调
- 🚚 **物流问题** — 物流异常、配送查询、地址修改
- 💬 **FAQ 问答** — 基于 RAG 的企业知识库检索
- 👨‍💼 **人工转接** — 复杂问题无缝转接人工客服

## 当前状态

**阶段：基础复现（feat/baseline-reproduction）**

当前为基于 [openai/openai-cs-agents-demo](https://github.com/openai/openai-cs-agents-demo)（MIT License）的可运行基线版本。Agent 仍为航旅客服场景，后续阶段将逐步改造为电商售后客服。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python + FastAPI |
| 智能体框架 | OpenAI Agents SDK |
| 前端框架 | Next.js + React |
| UI 组件 | ChatKit / ChatKit React |
| 知识检索 | RAG + 向量数据库（计划中） |
| 数据存储 | 内存存储（当前）→ SQLite / PostgreSQL（计划中） |

## 快速开始

### 前置要求

- Python ≥ 3.10
- Node.js ≥ 18
- OpenAI API Key（[获取方式](https://platform.openai.com/api-keys)）

### 1. 设置 API Key

```bash
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 或复制 .env.example 为 .env 并填入 Key
```

### 2. 启动后端

```bash
cd python-backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端运行在 **http://localhost:8000**

### 3. 启动前端

```bash
cd ui
npm install
npm run dev:next
```

前端运行在 **http://localhost:3000**

### 4. 运行测试

```bash
cd python-backend
source .venv/Scripts/activate
pip install pytest pytest-asyncio
pytest tests/ -v
```

### 详细文档

- [Baseline 复现运行手册](docs/baseline_runbook.md) — 完整启动步骤、验证流程、已知问题
- [架构基线](docs/architecture_baseline.md) — 系统架构和调用链
- [项目路线图](docs/project_roadmap.md) — 6 阶段开发规划

## 项目结构

```
commercecare-agent/
├── README.md
├── CLAUDE.md
├── LICENSE                     # MIT（来自上游）
├── NOTICE.md
├── .env.example
├── .gitignore
├── docs/
│   ├── upstream_audit.md
│   ├── architecture_baseline.md
│   ├── baseline_runbook.md
│   └── project_roadmap.md
├── python-backend/
│   ├── main.py                 # FastAPI 入口
│   ├── server.py               # ChatKit 服务端
│   ├── memory_store.py         # 内存存储
│   ├── requirements.txt
│   ├── tests/
│   │   └── test_baseline.py    # 基础测试
│   └── airline/
│       ├── agents.py           # 6 Agent + Handoff
│       ├── context.py          # Agent 上下文
│       ├── guardrails.py       # Guardrails
│       ├── tools.py            # 10 个工具函数
│       └── demo_data.py        # Mock 数据
└── ui/
    ├── app/                    # Next.js App Router
    ├── components/             # React 组件
    ├── lib/                    # API/类型/工具
    └── package.json
```

## 许可证

本项目基于 [openai/openai-cs-agents-demo](https://github.com/openai/openai-cs-agents-demo)（MIT License）。详见 [NOTICE.md](NOTICE.md) 和 [LICENSE](LICENSE)。

## 开发规范

详见 [CLAUDE.md](CLAUDE.md)。
