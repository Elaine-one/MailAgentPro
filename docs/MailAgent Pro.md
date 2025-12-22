

# 🧭 项目技术设计文档

## 📧 项目名称：MailAgent Pro（智能邮件助理）

**版本号：** v1.2.0
**编写日期：** 2025-12-21
**作者：** Elaine & Trae
**目标读者：** 开发工程师 / 架构师

---

## 1️⃣ 项目总体概述

MailAgent Pro 是一款基于 Python 和 PySide6 开发的**桌面端智能邮件群发系统**。它不仅集成了多账户管理、批量发送、变量替换等传统功能，还深度融合了 AI 大模型能力，能够实现邮件内容的智能生成、润色与多模型容错切换。

**核心价值：**
* **全能账户管理**：支持 SMTP 多账户配置，自动适配主流邮箱，授权码加密存储。
* **精准变量群发**：支持 `{name}` 等变量替换，实现“千人千面”的邮件内容。
* **AI 深度集成**：支持 OpenAI、通义千问、DeepSeek、Moonshot 等多模型，提供智能写信与内容解析。
* **工业级稳定性**：基于 SQLAlchemy 连接池管理，具备完善的错误重试机制与发送监控。
* **数据安全合规**：所有数据本地化存储，密钥硬件级隔离（模拟），确保隐私安全。

---

## 2️⃣ 系统架构总览

### 2.1 架构图（逻辑分层）

```
┌─────────────────────────────────────────────────────────────┐
│                       GUI 层 (PySide6)                      │
│   主窗口 / AI 侧边栏 / 账户管理 / 发送任务管理 / 历史记录查看器    │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
┌──────────────┴──────────────┐ ┌──────────────┴──────────────┐
│      应用核心层 (Core)      │ │      数据持久化 (Data)      │
│ ├─ AIWriter (LLM 客户端)     │ │ ├─ DBManager (SQLAlchemy)   │
│ ├─ MailSender (SMTP 引擎)    │ │ ├─ ConfigManager (JSON)     │
│ ├─ AccountManager (账户逻辑) │ │ └─ FileStorage (Logs/Key)   │
│ └─ TaskEngine (多线程调度)   │ └─────────────────────────────┘
└──────────────┬──────────────┘
               │
┌──────────────┴──────────────┐
│      外部接口 (External)    │
│ ├─ SMTP Servers (邮件传输)   │
│ └─ LLM APIs (AI 模型服务)    │
└─────────────────────────────┘
```

---

## 3️⃣ 核心模块设计

### 3.1 DBManager（数据库架构）
**技术栈：** SQLAlchemy + SQLite + QueuePool
**核心职责：**
* **连接池管理**：使用 `QueuePool` 缓存连接，解决多线程环境下数据库连接频繁创建的性能瓶颈。
* **健康监控**：`ConnectionPoolMonitor` 定期巡检，清理超时或失效连接，防止数据库死锁。
* **事务安全**：通过 `session_scope` 上下文管理器，确保数据库操作的原子性与自动回滚。

### 3.2 AIWriter（智能引擎）
**技术栈：** LangChain + 多供应商驱动
**核心职责：**
* **多模型兼容**：统一封装 OpenAI、通义千问、Moonshot 接口，支持流式与非流式输出。
* **智能解析**：内置启发式算法，自动从 AI 生成的 Markdown 内容中提取邮件主题与正文。
* **容错降级**：当主模型失效时，支持根据 API Key 自动切换备用供应商，确保服务高可用。

### 3.3 MailSender（发送引擎）
**技术栈：** SMTPLIB + QThread
**核心职责：**
* **变量渲染**：动态解析 `{name}`、`{variables}` 标签，实现个性化内容填充。
* **并发控制**：支持自定义发送间隔与线程数，内置重试逻辑（`send_round` 机制）。
* **SSL/TLS 支持**：支持 465/587 等多种端口安全协议。

---

## 4️⃣ 数据库设计（SQLite）

### 核心实体关系
* **Account (1) ↔ Task (N)**：一个账户可创建多个发送任务。
* **Task (1) ↔ TaskDetail (N)**：一个任务包含多个收件人的发送明细。

### 表结构摘要

#### `accounts`（邮箱账户）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| email | String | 发件地址 |
| auth_code | String | **加密存储**的授权码 |
| use_ssl | Boolean | 是否启用 SSL 安全连接 |

#### `recipients`（收件人库）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| email | String | 收件地址 |
| variables | Text | **JSON 格式**存储的自定义变量 |

#### `task_details`（发送明细）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| result | String | 成功/失败状态 |
| send_round | Integer | 当前重试轮次 |

---

## 5️⃣ 配置文件规范（config.json）

系统采用分层配置结构，重点在于 AI 配置的灵活性：

```json
{
  "ai_config": {
    "provider": "openai",
    "model": "gpt-4-turbo",
    "primary_key": "sk-...",
    "secondary_key": "sk-...",
    "max_tokens": 2048,
    "temperature": 0.7
  },
  "send_interval": 1,
  "send_threads": 3,
  "theme": "modern"
}
```

---

## 6️⃣ 目录结构规范

```
MailAgentPro/
├── app/
│   ├── core/           # 业务逻辑（AI驱动、数据库管理、邮件协议）
│   ├── ui/             # UI 组件（基于现代 QSS 皮肤）
│   ├── data/           # 数据存储（SQLite DB, Fernet Key）
│   ├── logs/           # 系统与 LLM 日志
│   └── config.json     # 全局配置
├── docs/               # 技术与用户文档
└── main.py             # 程序启动入口（包含 QProxyStyle 样式注入）
```

---

## 7️⃣ 开发与运行环境

* **Python 版本**：>= 3.9
* **核心依赖**：
    * `PySide6`: GUI 框架
    * `SQLAlchemy`: ORM 与连接池
    * `cryptography`: 数据加密
    * `langchain-openai` / `langchain-community`: AI 集成
    * `pandas`: 数据导入导出

---

## 8️⃣ 后续路线图 (Roadmap)

1. **RAG 知识库**：集成本地文档，让 AI 基于特定业务背景写信。
2. **定时任务**：支持离线定时发送队列。
3. **多语言支持**：实现全界面的国际化切换。
4. **统计报表**：可视化展示发送成功率与 AI 消耗统计。



