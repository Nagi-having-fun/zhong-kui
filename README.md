<p align="center">
  <img src="assets/logo.png" alt="钟馗 Logo" width="150" />
</p>

<h1 align="center">钟馗 / Zhong Kui</h1>

<p align="center">
  自动检测并驱除社交媒体中不想看到的内容 —— 以关键词匹配与 LLM 智能分类，守护你的信息流。
</p>

<p align="center">
  <img src="assets/banner.png" alt="钟馗 Banner" width="800" />
</p>

<p align="center">
  <a href="#功能特性">中文</a> | <a href="#features">English</a>
</p>

---

## 功能特性

- **辟邪** — 点击"没兴趣/不感兴趣"，驱除不想看到的帖子
- **除魔** — 屏蔽/拉黑发布不良内容的用户
- **双重检测** — 关键词快速扫描 + OpenAI GPT 智能语义分类
- **自定义规则** — 在 `unwanted_content.md` 中定义你不想看到的话题、关键词和内容模式
- **浏览器自动化** — 基于 Playwright 自动滚动信息流并执行操作
- **限速保护** — 随机延迟与操作预算，避免被平台检测为机器人
- **试运行模式** — 仅检测并记录，不执行任何操作

## 安装

### 1. 安装依赖

```bash
pip install playwright openai python-dotenv pyyaml
playwright install chromium
```

### 2. 配置 API Key

在项目根目录创建 `.env` 文件：

```
OPENAI_API_KEY=你的API密钥
```

### 3. 定义过滤规则

编辑 `unwanted_content.md`，添加你不想看到的话题、关键词和内容模式。

### 4. 调整设置（可选）

编辑 `config.yaml`：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `platform` | 平台：`"threads"`, `"x"`, `"both"` | `"threads"` |
| `max_actions_per_session` | 每次运行最大操作数 | `50` |
| `block_user` | 除魔：是否屏蔽用户 | `false` |
| `leave_comment` | 是否留下礼貌评论 | `false` |
| `detection.llm_model` | LLM 分类模型 | `gpt-4o-mini` |
| `detection.llm_confidence_threshold` | 最低置信度阈值 | `0.7` |

## 使用方法

### 首次运行（需要登录）

```bash
python -m src.main --platform threads --login --dry-run
```

1. 自动打开 Chromium 浏览器并导航到登录页面
2. 手动登录你的账号
3. 在终端按 **Enter** 继续
4. 工具开始滚动信息流并记录检测结果（试运行不执行操作）

### 试运行（仅检测）

```bash
python -m src.main --platform threads --dry-run
```

### 正式运行

```bash
# 仅辟邪（点击没兴趣）
python -m src.main --platform threads

# 辟邪 + 除魔（没兴趣 + 屏蔽用户）
python -m src.main --platform threads --block-user
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--platform threads\|x\|both` | 目标平台（默认读取 config.yaml） |
| `--login` | 强制重新登录 |
| `--dry-run` | 仅检测记录，不执行操作 |
| `--block-user` | 启用除魔（屏蔽用户） |
| `--max-actions N` | 覆盖每次最大操作数 |

### 推荐测试流程

1. `--dry-run` — 查看日志，确认检测准确度
2. `--dry-run --max-actions 10` — 检查是否有误报
3. `--max-actions 3` — 正式运行 3 次操作，观察浏览器行为
4. 确认无误后全量运行

## 项目结构

```
├── unwanted_content.md      # 过滤规则定义
├── config.yaml              # 运行配置
├── .env                     # API 密钥（已 gitignore）
├── src/
│   ├── main.py              # CLI 入口
│   ├── config.py            # 配置加载器
│   ├── rules_parser.py      # 解析 unwanted_content.md
│   ├── content_detector.py  # 关键词 + LLM 检测引擎
│   ├── browser_controller.py# Playwright 浏览器控制
│   ├── platforms/
│   │   ├── base_platform.py # 平台抽象接口
│   │   └── threads_platform.py # Threads 平台实现
│   └── utils/
│       ├── logger.py        # 日志与行为追踪
│       └── rate_limiter.py  # 限速与反检测
├── auth/                    # 保存的登录会话（已 gitignore）
└── logs/                    # 运行日志（已 gitignore）
```

---

<a name="features"></a>

## Features

- **Ward Off Evil (辟邪)** — Click "Not interested" to dismiss unwanted posts
- **Vanquish Demons (除魔)** — Block/mute users who post unwanted content
- **Two-tier detection** — Fast keyword scan + OpenAI GPT semantic classification
- **Configurable rules** — Define unwanted topics, keywords, and content patterns in `unwanted_content.md`
- **Browser automation** — Playwright-based feed scrolling and action execution
- **Rate limiting** — Randomized delays and action budgets to avoid bot detection
- **Dry-run mode** — Detect and log without taking any action

## Setup

### 1. Install dependencies

```bash
pip install playwright openai python-dotenv pyyaml
playwright install chromium
```

### 2. Configure API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your-api-key-here
```

### 3. Define content rules

Edit `unwanted_content.md` to add your unwanted topics, keywords, and content patterns.

### 4. Adjust settings (optional)

Edit `config.yaml`:

| Setting | Description | Default |
|---------|-------------|---------|
| `platform` | Target: `"threads"`, `"x"`, or `"both"` | `"threads"` |
| `max_actions_per_session` | Max actions per run | `50` |
| `block_user` | Vanquish Demons: block users | `false` |
| `leave_comment` | Leave a polite comment | `false` |
| `detection.llm_model` | LLM model for classification | `gpt-4o-mini` |
| `detection.llm_confidence_threshold` | Minimum confidence threshold | `0.7` |

## Usage

### First run (login required)

```bash
python -m src.main --platform threads --login --dry-run
```

1. Opens Chromium browser and navigates to login page
2. Log in manually in the browser
3. Press **Enter** in terminal to continue
4. Tool scrolls feed and logs detected posts (no actions in dry-run mode)

### Dry run (detect only)

```bash
python -m src.main --platform threads --dry-run
```

### Live run

```bash
# Ward Off Evil only (click "Not interested")
python -m src.main --platform threads

# Ward Off Evil + Vanquish Demons (dismiss + block user)
python -m src.main --platform threads --block-user
```

### CLI flags

| Flag | Description |
|------|-------------|
| `--platform threads\|x\|both` | Target platform (default: from `config.yaml`) |
| `--login` | Force re-login (use if session expired) |
| `--dry-run` | Detect and log only, take no action |
| `--block-user` | Enable Vanquish Demons (block users) |
| `--max-actions N` | Override max actions per session |

### Recommended test sequence

1. `--dry-run` — Review log for detection accuracy
2. `--dry-run --max-actions 10` — Check for false positives
3. `--max-actions 3` — Live test with 3 actions while watching browser
4. Full run once confident

## License

MIT
