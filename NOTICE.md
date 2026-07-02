# NOTICE

## 上游项目声明

本项目 **CommerceCare Agent** 在架构设计和技术实现上参考了以下开源项目：

- [openai/openai-cs-agents-demo](https://github.com/openai/openai-cs-agents-demo)

## 许可证

上游项目采用 **MIT License**，版权所有 © 2025 OpenAI。

```
Copyright 2025 OpenAI

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 归属说明

- 本项目复用了上游项目的多智能体编排模式（Triage → Specialist → Handoff）、Guardrail 机制和 ChatKit 前后端集成方式。
- 本项目将上游的**航旅客服场景**改造为**电商售后客服场景**，Agent 角色、工具调用和知识库内容均为独立实现。
- 本项目并非上游项目的 Fork，而是以其为参考的独立改造项目。

## 引用依赖

本项目依赖以下由 OpenAI 提供的开源库：

| 库 | 许可证 | 用途 |
|---|---|---|
| `openai-agents` | MIT | 多智能体编排 SDK |
| `openai-chatkit` | MIT | 聊天 UI 服务端集成 |
| `@openai/chatkit-react` | MIT | 聊天 UI 前端组件 |
