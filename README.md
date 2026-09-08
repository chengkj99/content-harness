# Content Harness

把内容创作保存成可检查、可返工、可继续的本地工作流。

Agent 负责调研、写作和评审；CLI 负责资产依赖、版本、事实台账、审批与交付。每篇文章有独立工作目录，换客户端或中断后仍能从磁盘继续。项目独立运行，不依赖其他私有 Skills 或个人 Wiki。

当前版本 `0.1.0`：中文公众号长文的 M0/M1 初始实现。提供可选的“公众号高传播”“去 AI 味”风格和按场景隔离的风格反馈。只交付本地发布包，没有公众号自动发布、模型 API 或后台服务。

## 安装

需要 Python 3.11+，支持 macOS/Linux。先安装 [uv](https://docs.astral.sh/uv/)，再执行：

```bash
uv tool install 'git+https://github.com/chengkj99/content-harness.git'
content-harness version
```

尚未发布到 PyPI，不要直接执行 `uv tool install content-harness`。

## 第一次写文章

在你保存文章的项目目录执行：

```bash
content-harness init .
content-harness install-skills --client codex
```

编辑 `.content-harness/author-profile.md`，填写真实的读者、表达习惯与经历边界，再由你在终端确认：

```bash
content-harness confirm-author
content-harness doctor
```

默认安装到项目级 `.agents/skills/`；Claude Code 使用 `--client claude`，Cursor 使用 `--client cursor`。安装后重新载入客户端。这三种安装目录已做自动化检查，真实客户端行为兼容仍待验证。

在 Agent 客户端里说：

> 使用 Content Harness，把“为什么资料收藏了很多，动手时还是没有下一步”做成公众号文章。先整理证据、明确读者与核心判断，完成简报后等我确认。

Agent 会创建 run、保存来源与主张台账、生成简报，并给出审批命令。你读过简报后执行：

```bash
content-harness approve <run-id> brief
```

按提示输入完整哈希，再告诉 Agent 继续。默认不强制高传播或口语化。若需要，可以说：

> 这篇使用公众号高传播风格，中等强度，最后去 AI 味。保留数字、引用、限定词和我的真实经历。

对应命令：

```bash
content-harness style <run-id> \
  --use wechat-high-engagement \
  --use natural-human-zh \
  --intensity medium
```

Agent 完成提纲、正文、润色、两类评审、必要配图与发布包后，你确认最终内容并导出：

```bash
content-harness approve <run-id> publish
content-harness export <run-id> --target wechat
```

这一步只导出本地文件，不会发送到公众号。

## 最后得到什么

```text
你的内容项目/
├── .content-harness/
│   ├── project.yaml
│   ├── author-profile.md
│   ├── style-memory/          # 作者/场景偏好、候选、历史版本
│   └── runs/<run-id>/
│       ├── workflow.yaml     # 固化本次 DAG
│       ├── manifest.yaml     # 当前状态
│       ├── transitions.jsonl # 可重放事件
│       ├── approvals.jsonl
│       ├── snapshots/        # 已登记内容快照
│       └── artifacts/        # 想法、来源、提纲、正文、评审、图片、发布包
└── content/<run-id>/
    ├── article.md
    ├── titles.txt
    ├── summary.txt
    ├── sources.yaml
    ├── images.yaml
    └── assets/               # 有图时存在
```

先看 [演示文章](examples/article.md) 和 [逐步指南](docs/usage.md)。演示文本不是已发布文章或效果实验。

## 返工与风格积累

手改正文后执行 status，下游会被标为 stale。Agent 重新处理受影响资产，保留仍有效的调研和简报。

```bash
content-harness status <run-id> --json
content-harness resume <run-id> --json
content-harness style <run-id> --reset
```

人工改稿后，在登记新稿之前记录反馈：

```bash
content-harness style-feedback <run-id> \
  --artifact manuscript --scope scenario --reason '结尾要给出具体动作'
```

让 Agent 根据差异填写候选规则及评估样例。确认值得长期使用后，你执行 `style-promote <run-id> <lesson-id>`。作者与不同场景分别保存版本，可用 style-rollback 恢复旧规则；新记忆不会改变历史文章。

## 在 kj-llm-wiki 使用

在该 Wiki 根目录执行：

```bash
content-harness init . --preset wiki
content-harness install-skills --client codex
```

过程文件在 `.content-harness/runs/`，成品输出到 `raw/studio/funnel/formatted/wechat/<run-id>/`。初始化不移动旧内容、不写正式 wiki 页面。接入前读取项目自己的 AGENTS.md、SCHEMA.md 并核对配置，见 [Wiki 接入](docs/wiki-integration.md)。

## 验证与限制

- 自动化验证覆盖 DAG 失效、手改保护、审批失效、日志恢复、并发锁、导出冲突、风格事实差异、场景记忆及 CLI 安装。
- 三套风格与 13 个独立 Skills 随 Python 安装包携带。
- 字符串门禁只能发现部分事实错误；主张是否成立、表达是否改变含义仍需语义评审及必要人工核验。不承诺任意改写的语义保真或“爆款”。
- 本地 TTY 审批是流程控制，不是身份认证，不能对抗与用户共享文件和命令权限的恶意 Agent。
- 未完成真实模型行为评估、三客户端完整试用、10 篇真实文章试用或传播效果验证。见 [验证报告](docs/validation.md)。

## 开发

```bash
git clone https://github.com/chengkj99/content-harness.git
cd content-harness
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run python scripts/export_schemas.py --check
uv build
```

源码在 src/content_harness/，资源在其 resources/ 中，随 wheel 分发。JSON Schema 在 schemas/，由 Pydantic 模型生成。详见 [架构说明](docs/architecture.md)。

许可证沿用仓库原有的 [Apache-2.0](LICENSE)。
