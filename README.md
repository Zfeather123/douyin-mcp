# douyin-mcp

让 AI Agent 读取、理解并分析你在抖音创作者中心真实可见的数据。

> [!IMPORTANT]
> **平台条款风险：** 本项目是非官方社区工具，未获抖音或其关联公司授权、认可或背书。抖音用户服务协议第 2.4、5.1、5.3 和 7.1 条涉及非商业许可、自动化访问、平台外处理或展示信息、向第三方提供信息以及账号处置风险。本项目使用 Playwright 驱动浏览器；即使只读取本人账号中可见的数据，也仍可能违反平台条款或触发账号风控。使用前必须阅读 [平台合规与非官方声明](PLATFORM_COMPLIANCE.md)，并自行确认已取得必要书面授权。AGPL 允许商业使用本项目代码，但不授予访问抖音、商业使用平台或数据、向第三方提供平台信息或使用抖音商标的权利。

## 这是什么？

`douyin-mcp` 是一个面向个人创作者的本地 MCP Server。

它在你的电脑上运行，复用专用 Chrome 的抖音登录状态，把创作者中心页面中的作品和经营指标保存到本地 SQLite，再通过 MCP 协议提供给支持 MCP 的 Agent。

可以把它理解为一座桥：

```text
抖音创作者中心  →  本地结构化数据  →  MCP  →  AI Agent
```

它解决的是“Agent 看不到我的创作者数据”这个具体问题。当前范围是 **Windows、本机运行、单用户、单抖音账号**；不提供多账号托管、云端采集或未公开接口抓取。

## 它能做什么？

### 获取你真实可见的数据

- 首次使用或登录失效时打开可见 Chrome，让你扫码或完成安全验证。
- 后续复用专用浏览器 profile，通常不需要重复登录。
- 增量读取虚拟滚动作品列表，保存播放、点赞、评论、分享和收藏等页面可见指标。
- 按需分批读取作品详情，采集完播率、5 秒完播率、平均观看时长、曝光和涨粉等可见指标。

### 让 Agent 查询和分析

- 查询作品列表、单条作品表现和历史快照。
- 对比 2～20 条作品的关键指标。
- 计算点赞率、收藏率、评论率、分享率、播放率和互动率。
- 使用透明、带版本的规则进行轻量潜力排序。
- 生成带数据时间、覆盖率、缺失项和证据引用的复盘上下文。
- 导出 JSON 或 CSV，便于进一步分析或备份。

### 帮你判断结论是否可信

- 返回缓存新鲜度、字段覆盖率、缺失原因和质量警告。
- 页面未显示的值保存为 `null`，不会用 0 或猜测值填充。
- 列表与详情分别保存为快照，不会混写来源。
- 首次成功同步后绑定当前账号，误切账号时拒绝写入。

## 工作方式与边界

这套方案在技术上只使用当前用户的登录状态和页面可见内容，并把浏览器操作、数据结构化和 Agent 推理分成了清晰的三层：

1. **浏览器层**：Playwright 操作项目专用 Chrome，读取你在抖音创作者中心页面上真实可见的内容。它不能绕过登录、权限或平台验证。
2. **数据层**：本地服务将页面内容规范化为作品、指标快照、同步任务和质量状态，保存在本机 SQLite。
3. **MCP 层**：FastMCP 把同步、查询、对比和复盘能力暴露为标准工具，Agent 不需要直接操作 Cookie 或理解页面 DOM。

这也是它能兼顾安全和可审计性的原因：登录凭证留在专用浏览器 profile 中，MCP 只返回业务数据和质量信息；每个分析结果都可以追溯到采集时间、数据来源和快照。

这些技术边界不代表抖音已经允许自动化访问。平台条款、专项规则和实际授权始终优先于项目功能说明；本项目不支持绕过登录、安全验证、权限、风控或技术保护，也不支持多账号托管、云端代采和数据转售。

## 5 分钟快速开始

### 环境要求

- Windows 10/11
- Python 3.11 或更高版本
- Google Chrome
- 一个支持 MCP 和终端操作的 Agent

### 一句话安装

直接告诉 Agent：

```text
帮我克隆并安装 https://github.com/Kuhakucai/douyin-mcp 项目
```

Agent 应完成克隆并运行 `easy-install.ps1`。脚本会创建项目专用 `.venv`、安装依赖、创建默认 `.env`、初始化数据库并执行环境诊断。

首次扫码、修改 MCP 客户端配置和同步真实数据前，Agent 应先向你展示平台风险并征得确认。阅读 `PLATFORM_COMPLIANCE.md` 后，由你明确授权 Agent 运行：

```powershell
douyin-mcp acknowledge-platform-risk --yes
```

如果已经克隆项目，可直接运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\easy-install.ps1
```

### 接入 MCP 客户端

安装结束时，`douyin-mcp init` 会输出包含本机绝对路径的 `mcp_config`。把它加入你的 MCP 客户端，然后重启客户端或新建会话。

通用配置结构如下；实际使用时请以 `init` 输出为准：

```json
{
  "mcpServers": {
    "douyin-creator": {
      "command": "D:/path/to/douyin-mcp/.venv/Scripts/python.exe",
      "args": ["-m", "douyin_creator_mcp.server"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "DATA_DIR": "D:/path/to/douyin-mcp/data",
        "DOUYIN_BROWSER_PROFILE_DIR": "D:/path/to/douyin-mcp/data/browser-profile"
      }
    }
  }
}
```

### 完成首次同步

确认平台风险并连接成功后，可以直接对 Agent 说：

```text
检查我的抖音数据状态。如果还没有登录，打开浏览器让我扫码；
登录后同步作品列表，再分批同步最近 20 条作品详情。
完成后告诉我数据时间、字段覆盖率、缺失项和质量警告。
```

登录窗口不需要一直置顶。同步时可以切换到其他软件，但不要关闭专用 Chrome、切换账号或手动跳转页面。

## 推荐的 Agent 用法

日常使用时，优先检查缓存新鲜度，再决定是否打开浏览器同步：

```text
检查我的抖音数据状态。只在缓存过期时更新作品列表和最近 20 条详情；
然后按最近 30 天比较完播率、5 秒完播率和互动率，给出复盘结论。
每条结论都说明数据时间、覆盖率、缺失项和对应作品证据。
```

也可以直接提出具体问题：

- “找出最近 30 天互动率最高的 5 条作品，并说明共同点。”
- “对比这 3 条视频的完播率、收藏率和涨粉表现。”
- “哪些作品值得做续集？说明排序依据和数据局限。”
- “导出全部历史快照为 JSON。”

## 手动安装与 CLI

不使用 Agent 时，可以手动安装：

```powershell
git clone https://github.com/Kuhakucai/douyin-mcp.git
cd douyin-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
douyin-mcp init
douyin-mcp doctor
douyin-mcp acknowledge-platform-risk --yes
```

常用命令：

```powershell
# 首次登录或登录失效时使用
douyin-mcp login --timeout 180

# 同步作品列表
douyin-mcp sync

# 查看作品并取得 video_id
douyin-mcp videos --limit 20

# 每批最多处理 10 条；根据 next_cursor 继续
douyin-mcp details --recent-limit 20
douyin-mcp details --recent-limit 20 --cursor 10

# 查询单条作品表现
douyin-mcp performance <video_id> --period 30d

# 查看登录、缓存、任务和覆盖率
douyin-mcp status
```

完整 CLI：

| 命令 | 用途 |
|---|---|
| `init` | 初始化目录和数据库，输出 MCP 配置 |
| `doctor` | 检查运行环境，不打开浏览器 |
| `acknowledge-platform-risk` | 确认已阅读并理解平台自动化访问风险 |
| `login` | 打开浏览器并等待登录 |
| `status` | 查看登录、缓存、同步任务和覆盖率 |
| `sync` | 同步作品列表和列表页指标 |
| `details` | 分批同步指定或近期作品详情 |
| `videos` | 分页查询本地作品 |
| `performance` | 查询单条作品快照和派生指标 |
| `export` | 导出 JSON 或 CSV |
| `purge` | 清除本地数据和专用浏览器 profile |

## MCP 工具

默认入口提供 13 个浏览器数据工具：

| 工具 | 用途 |
|---|---|
| `douyin_browser_login_start` | 打开可见 Chrome，处理首次登录或重新登录 |
| `douyin_browser_login_status` | 查询当前浏览器登录状态 |
| `douyin_browser_get_status` | 查询新鲜度、任务、覆盖率、账号绑定和 profile 锁 |
| `douyin_browser_sync_if_needed` | 按 TTL 同步列表、详情或全部数据 |
| `douyin_browser_sync_creator_data` | 同步作品列表和列表指标 |
| `douyin_browser_sync_video_details` | 分批同步指定或近期作品详情指标 |
| `douyin_browser_list_videos` | 分页查询作品和最新指标 |
| `douyin_browser_get_video_performance` | 查询单作品快照和派生指标 |
| `douyin_browser_compare_videos` | 对比 2～20 条作品 |
| `douyin_browser_get_metric_coverage` | 查询字段覆盖率和缺失原因 |
| `douyin_browser_rank_video_potential` | 使用透明、带版本的规则进行轻量排序 |
| `douyin_browser_generate_review` | 生成带证据和警告的复盘上下文 |
| `douyin_browser_export_data` | 导出 JSON 或 CSV |

所有工具使用内部账号键 `browser-default`，无需 Agent 传递账号 ID。常见业务状态包括 `completed`、`partial`、`cache_hit` 和 `user_action_required`。

## 工作原理

```text
MCP Client / Agent
        │ stdio
        ▼
douyin_creator_mcp.server
        │
        ├── BrowserService ── Playwright ── 专用 Chrome profile
        │
        └── Database ── data/douyin.sqlite
```

列表同步负责发现作品和采集列表页指标；详情同步按批次访问作品详情页。两种来源分别保存为快照，不会互相覆盖。派生比率只使用同一个原始快照的分子和分母，并记录公式版本。

## 数据可靠性与平台边界

- 页面显示什么就保存什么；未显示的值是 `null`，不会用 0 或推测值填充。
- 写入详情前校验作品身份；无法确认时拒绝写入。
- 同一批次、同一作品、同一来源只写一个快照；失败同步不会覆盖历史可信快照。
- `period=30d` 等周期按快照采集时间筛选，`all` 表示全部本地历史。
- 部分作品可能被平台标记为暂不支持详情数据，此时返回 `partial`、失败原因和续跑游标。
- 潜力排序在样本少于 10 条时仅供参考，不代表平台官方评分。
- 页面 DOM、字段可见性和风控策略可能变化，使用时应关注覆盖率和质量警告。

## 登录态、账号与并发

- 登录状态保存在 `data/browser-profile/`，所以再次启动通常不需要扫码。
- 首次成功列表同步会用作品标题和发布时间摘要建立不可逆账号指纹，不保存昵称、原始标题或作品 ID 作为身份信息。
- 检测到账号变化时返回 `account_mismatch` 并拒绝写入。
- 同一 profile 同时只允许一个同步进程；死亡进程留下的锁会在安全确认后自动恢复。
- 确认要更换账号时，运行 `douyin-mcp purge --yes`，然后重新登录和同步。

## 本地数据与隐私

```text
data/
├── browser-profile/    # 专用 Chrome 登录状态
├── douyin.sqlite       # 作品、指标快照和同步任务
├── exports/            # JSON/CSV 导出
├── reports/            # 本地复盘产物
└── logs/
```

这些目录、数据库、备份和浏览器诊断产物均被 `.gitignore` 排除。不要使用 `git add -f` 提交它们。

MCP 不会把 Cookie、localStorage、sessionStorage、验证码或账号密码返回给 Agent。但作品标题以及你主动查询的创作数据会进入 Agent 上下文；如果 Agent 使用云端模型，应同时遵守对应模型服务的数据政策。

导出与清除：

```powershell
douyin-mcp export --format json --period all
douyin-mcp export --format csv --period 30d

# 不带 --yes 时只显示确认提示
douyin-mcp purge
douyin-mcp purge --yes
```

`purge --yes` 会删除数据库、数据库备份、导出、报告和专用浏览器 profile，此操作不可恢复。

## 常见问题

### PowerShell 找不到 `douyin-mcp`

激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

或者直接使用：

```powershell
.\.venv\Scripts\douyin-mcp.exe doctor
```

### PowerShell 阻止安装脚本

下面的执行策略只作用于本次命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\easy-install.ps1
```

### 登录后仍提示需要操作

保持专用 Chrome 打开，完成扫码、验证码或安全验证，再重试同步。不要使用日常 Chrome profile 替换项目的专用 profile。

### 返回 `profile_in_use`

另一个同步进程仍在使用专用浏览器。等待它结束后重试；如果原进程已经退出，锁会在安全确认后自动恢复。

### 详情同步返回 `partial`

查看 `failures`、`coverage` 和 `next_cursor`。常见原因是作品状态暂不支持查看详情、页面未展示某项指标，或当前批次仍需继续。

## 开发者指南

### 开发环境

```powershell
git clone https://github.com/Kuhakucai/douyin-mcp.git
cd douyin-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

### 项目结构

```text
src/douyin_creator_mcp/
├── server.py                 # FastMCP 入口和 browser-only 容器
├── cli.py                    # 用户 CLI
├── config.py                 # 环境配置
├── browser/
│   ├── session.py            # Playwright 与持久化 profile
│   ├── extractors.py         # 列表/详情提取和规范化
│   └── profile_lock.py       # 跨进程 profile 锁
├── services/
│   ├── browser_service.py    # 同步、查询、对比、复盘和导出
│   └── metrics.py            # 派生指标与排序公式
├── storage/
│   ├── db.py                 # SQLite、迁移与备份
│   └── schemas.sql           # 数据表结构
└── tools/
    └── browser_tools.py      # 13 个 MCP 工具契约

easy-install.ps1              # Windows 一键安装
```

### 扩展原则

新增能力时建议保持以下边界：

1. 页面读取和 DOM 处理放在 `browser/`。
2. 可测试的业务逻辑放在 `services/`。
3. MCP 工具只做参数声明、服务调用和统一错误响应。
4. 原始数据、派生指标和不同采集来源分开保存。
5. 新字段必须定义缺失语义、数据来源、解析版本和测试样例。
6. 不读取或返回浏览器认证材料，不接入未公开私有接口。

### 基础验证

```powershell
python -m compileall -q src
```

### 真实浏览器验收

涉及 DOM、指标提取或浏览器生命周期的变更，还应使用测试账号运行：

```powershell
douyin-mcp doctor
douyin-mcp login --timeout 180
douyin-mcp sync
douyin-mcp details --recent-limit 5
douyin-mcp status
```

验收时应核对登录态复用、页面声明数量、加载数量、解析数量、重复同步幂等性、详情身份校验、覆盖率和失败原因。真实账号数据和验收产物不得提交到仓库。

## 免责声明

`douyin-mcp` 是独立维护的第三方开源项目，不是抖音、字节跳动或其关联公司的官方、授权、认证或合作产品。用户必须自行确认拥有合法账号、数据访问权以及自动化访问、平台外处理或展示、向 Agent 或模型服务提供数据所需的全部书面授权。

本项目不会通过 MCP 返回 Cookie、localStorage、sessionStorage、验证码或账号密码，但作品信息和经营数据会进入 MCP 客户端及 Agent 上下文；使用云端模型时，相关服务可能接收、记录或处理这些数据。“本机运行”不表示业务数据一定不会离开本机。

在适用法律允许的最大范围内，本项目按“原样”提供，不保证平台持续可访问、账号不受限制、数据完整准确或页面解析持续有效。使用者应自行评估账号限制或封禁、内容或数据删除、权益无法访问、业务中断、隐私泄露及错误分析等风险。完整边界见 [平台合规与非官方声明](PLATFORM_COMPLIANCE.md)。

## 开源协议

Copyright (C) 2026 Kuhakucai。`Kuhakucai` 与 `Puppetsho` 是同一作者使用的 Git 提交身份，详见 [AUTHORS.md](AUTHORS.md)。

本项目基于 [GNU Affero General Public License v3.0](LICENSE)（`AGPL-3.0-only`）开源。分发本项目或修改版时必须继续使用兼容的 AGPL 许可并提供对应源码；修改版通过网络与用户交互时，还必须按 AGPL 第 13 条向这些用户提供对应源码。AGPL 允许商业使用，但不允许闭源分发修改版，也不允许在不向网络用户提供对应源码的情况下把修改版作为网络服务运行。

AGPL 要求按其条款向接收者或符合条件的网络用户提供对应源码，不等于所有私人修改都必须发布到公共 GitHub 仓库，也不禁止收费或商业使用代码。

许可证只覆盖本项目代码和随附文档，不授予任何抖音平台访问权、数据权、商业使用权或商标权。抖音平台条款与代码许可证是两个独立层次；即使代码使用符合 AGPL，平台访问和数据处理仍可能需要抖音的事先书面授权。使用与贡献前请阅读 [平台合规声明](PLATFORM_COMPLIANCE.md) 和 [贡献指南](CONTRIBUTING.md)。
