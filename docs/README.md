# MailAgent Pro

> 智能邮件助理 —— AI 辅助撰写，多账户批量发送，面向生产环境的性能与稳定性优化。

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.4%2B-green)](https://www.qt.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)](https://www.microsoft.com/windows)

---

## 📖 简介

MailAgent Pro 是一款面向办公自动化的邮件发送工具，集成 AI 写作、模板管理、多账户管理与高并发发送能力。项目重点关注稳定性和性能，通过连接池、流式附件处理与智能重试机制降低资源占用和发送失败率。

---

## ✨ 核心特性

| 功能 | 描述 |
|------|------|
| 🤖 **AI 智能撰写** | 邮件生成、润色、翻译、摘要与主题生成 |
| 📧 **高性能发送** | SMTP 连接池复用、流式附件处理、后台资源清理 |
| 👥 **多账户管理** | 支持多邮箱账户，灵活切换发送 |
| 📋 **模板系统** | 预设模板管理，快速生成专业邮件 |
| 🔄 **智能重试** | 错误分类与指数退避重试策略 |
| 📊 **发送历史** | 完整的发送记录与审计日志 |
| 🎨 **现代界面** | 基于 PySide6 的扁平化设计 |

---

## 📂 项目结构

```
MailAgentPro/
├── app/                      # 应用主目录
│   ├── core/                 # 核心模块
│   │   ├── account_manager.py    # 账户管理
│   │   ├── ai_writer.py          # AI 写作引擎
│   │   ├── mail_sender.py        # 邮件发送引擎
│   │   ├── template_manager.py   # 模板管理
│   │   ├── recipient_manager.py  # 收件人管理
│   │   └── path_manager.py       # 路径管理
│   ├── db/                   # 数据库模块
│   │   └── db_manager.py         # SQLite + ORM 封装
│   ├── ui/                   # 界面模块
│   │   ├── main_window.py        # 主窗口
│   │   ├── ai_sidebar.py         # AI 侧边栏
│   │   ├── email_sender.py       # 邮件发送界面
│   │   └── ...                   # 其他界面组件
│   ├── data/                 # 数据目录
│   │   ├── mail_sender.db        # 数据库文件
│   │   ├── config.json           # 配置文件
│   │   ├── templates.json        # 邮件模板
│   │   └── encryption.key        # 加密密钥
│   ├── logs/                 # 日志目录
│   ├── backups/              # 备份目录
│   ├── exports/              # 导出目录
│   └── main.py               # 应用入口
├── docs/                     # 文档目录
│   ├── README.md                 # 项目说明
│   └── requirements.txt          # 依赖列表
└── windows/                  # 安装程序目录
    └── MailAgentPro_v1.0.0_Setup.exe  # 安装程序
```

---

## ⚙️ 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.9+ |
| 操作系统 | Windows 10/11 |
| 依赖 | PySide6, openai, pandas, cryptography |

---

## 🚀 快速开始

### 方式一：安装程序（推荐）

1. 下载 `windows/MailAgentPro_v1.0.0_Setup.exe`
2. 双击运行安装程序
3. 按照安装向导完成安装
4. 启动 MailAgent Pro

### 方式二：从源码运行

#### 1️⃣ 克隆项目

```bash
git clone https://github.com/Elaine-one/MailAgentPro.git
cd MailAgentPro
```

#### 2️⃣ 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 安装依赖
pip install -r docs/requirements.txt
```

#### 3️⃣ 启动应用

```bash
python app/main.py
```

---

## 🔧 配置说明

首次运行后，程序会在 `app/data/` 目录下自动生成 `config.json`。

### AI 配置示例

```json
{
  "ai_config": {
    "provider": "OpenAI",
    "model": "gpt-3.5-turbo",
    "primary_key": "your-api-key",
    "max_tokens": 2048,
    "temperature": 0.7
  }
}
```

### 支持的 AI 提供商

| 提供商 | 模型示例 |
|--------|---------|
| OpenAI | gpt-3.5-turbo, gpt-4 |
| 通义千问 | qwen-turbo, qwen-plus |
| Moonshot | moonshot-v1-8k |

---

## 📸 界面预览

| 界面 | 说明 |
|------|------|
| 主界面 | 标签页布局，包含账户、收件人、撰写、发送、历史、设置 |
| AI 侧边栏 | 滚轮选择器，支持邮件生成、摘要、翻译 |
| 邮件撰写 | AI 辅助写作，模板管理 |
| 邮件发送 | 多账户切换，批量发送 |

---

## 🔑 核心技术

- **连接池技术**：SMTP 连接复用，减少握手开销
- **流式处理**：大附件流式读取，降低内存占用
- **智能重试**：指数退避算法，自动重试失败任务
- **数据加密**：敏感信息加密存储，保护账户安全

---

## ❓ 常见问题

<details>
<summary><b>Q: 邮件发送失败如何排查？</b></summary>

1. 检查 SMTP 服务器地址和端口是否正确
2. 确认邮箱已开启 SMTP 服务
3. 检查网络连接是否正常
4. 查看发送历史中的错误信息
5. 程序会自动重试多次并记录详细日志
</details>

<details>
<summary><b>Q: 如何配置 AI 功能？</b></summary>

1. 进入"设置"标签页
2. 选择 AI 提供商（OpenAI/通义千问/Moonshot）
3. 输入 API Key
4. 点击"测试连接"验证配置
5. 保存设置后即可使用 AI 功能
</details>

<details>
<summary><b>Q: 如何批量导入收件人？</b></summary>

1. 准备 Excel/CSV 文件
2. 进入"收件人管理"标签页
3. 点击"导入收件人"
4. 选择文件并映射字段
5. 确认导入
</details>

---

## 📝 开发指南

### 代码风格

- 遵循 PEP8 规范
- 使用类型注解
- 函数添加文档字符串

### 关键文件

| 文件 | 说明 |
|------|------|
| `app/core/mail_sender.py` | 发送逻辑、连接池与流式附件处理 |
| `app/core/ai_writer.py` | AI 提供商适配与调用封装 |
| `app/db/db_manager.py` | 数据模型与数据库连接实现 |
| `app/ui/main_window.py` | 主窗口与界面逻辑 |

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证，详情请参阅 [LICENSE](../LICENSE) 文件。

---

## 📧 联系方式

- 技术支持：elaine
- 邮箱：onee20589@gmail.com
- GitHub：https://github.com/Elaine-one/MailAgentPro

---

## 🙏 致谢

- [PySide6](https://www.qt.io/) - Qt for Python
- [OpenAI](https://openai.com/) - GPT API
- [通义千问](https://tongyi.aliyun.com/) - 阿里云大模型
- [Moonshot](https://moonshot.cn/) - Kimi API

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star！⭐**

</div>
