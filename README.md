# CommerceCare Agent

基于多智能体、RAG、工具调用与人工转接的电商售后智能客服系统。

## 项目简介

CommerceCare Agent 是一个智能电商售后客服系统，采用多智能体协作架构，能够自动处理：

- 📦 **订单查询** — 订单状态、物流追踪、订单详情
- 🔄 **退换货处理** — 退款申请、退货流程、换货协调
- 🚚 **物流问题** — 物流异常、配送查询、地址修改
- 💬 **FAQ 问答** — 基于 RAG 的企业知识库检索
- 👨‍💼 **人工转接** — 复杂问题无缝转接人工客服

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python + FastAPI |
| 智能体框架 | OpenAI Agents SDK |
| 前端框架 | Next.js + React |
| UI 组件 | ChatKit / ChatKit React |
| 知识检索 | RAG + 向量数据库 |
| 数据存储 | SQLite / PostgreSQL |

## 快速开始

> ⚠️ 项目开发中，快速开始指南将在基础复现阶段完成后补充。

## 项目结构

```
commercecare-agent/
├── README.md
├── CLAUDE.md
├── NOTICE.md
├── .env.example
├── .gitignore
├── docs/
│   ├── upstream_audit.md
│   ├── architecture_baseline.md
│   └── project_roadmap.md
├── python-backend/          # Python 后端（待创建）
└── ui/                      # Next.js 前端（待创建）
```

## 许可证

本项目参考了 [openai/openai-cs-agents-demo](https://github.com/openai/openai-cs-agents-demo)（MIT License）。详见 [NOTICE.md](NOTICE.md)。

## 开发规范

详见 [CLAUDE.md](CLAUDE.md)。
