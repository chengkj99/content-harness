# Content Harness 使用手册

本手册整合了项目用途、安装、写作流程、命令速查和排错入口，适合想在一份文档中了解全貌的读者。分主题的详细文档见文末[阅读导航](#阅读导航)。

## 一、这个项目是做什么的

Content Harness 是一套给 AI 用的写作流程和工具，帮你把一个想法做成**有依据、可修改、能接着写**的文章：

- **你负责**：提出主题和素材、确认文章方向、审阅最终稿。
- **AI 负责**：查资料、列提纲、写正文、调整表达、检查事实，并通过 CLI 调用 Content Harness。
- **Content Harness 负责**：保存写作过程的每一步状态，让你中途退出后能继续，也能在改稿后知道哪些检查需要重做。

它当前主要服务**中文长文创作**，内置流程首先面向公众号文章。文章以 Markdown 文本和本地图片交付，可保存到普通文件夹、Git 仓库或 LLM Wiki 知识库。

### 它不做什么

- 没有一键发布到公众号或其他平台的功能（`publish` 只是确认命令的名称，导出仅落到本地目录）。
- 不包含模型服务；需要搭配一个能读写本地文件、执行命令并使用 Skills 的 AI 客户端（如 Codex、Claude Code、Cursor）。
- “高传播风格”“去 AI 味”是表达策略和编辑要求，不是阅读量或检测器通过率的承诺。

## 二、核心概念

| 概念 | 含义 |
|---|---|
| 写作项目 | 你在电脑上选定的一个文件夹，素材和文章都围绕它组织 |
| run | 一篇文章的一次工作记录，有自己的编号（如 `2026-09-09-material-to-action`）、稿件、修改记录和检查结果 |
| 资产（artifact） | 写作过程的中间产物：idea、sources、claims、brief、outline、draft、manuscript、各类 review、publish-package 等，构成一个依赖 DAG |
| stale | 上游资产改过，这个结果需要重新处理（不表示文件被删除） |
| Skills | 给 AI 看的操作指引，共 13 个，安装到 AI 客户端可发现的目录 |
| 场景（scenario） | 风格记忆的分组，例如 book-notes、product-notes，让不同类型文章分别积累表达偏好 |
| 哈希指纹 | 每次人工确认时需输入的 `sha256:` 开头字符串，绑定你审阅时的内容版本，改稿后需重新确认 |

过程状态固定保存在项目的隐藏目录 `.content-harness` 中；你通常只需看成品目录。

## 三、安装与初始化

支持 macOS / Linux，需要 Python 3.11+ 和 uv。最省事的方式是把[新手上手指南](getting-started.md#第一次准备)中的提示词发给 AI，让它检查环境并代为安装。手动安装：

```bash
uv tool install 'git+https://github.com/chengkj99/content-harness.git'
content-harness version
content-harness doctor            # 检查环境是否就绪
```

在写作项目中初始化并安装 Skills：

```bash
content-harness init . --preset wiki                # 创建配置，不生成文章
content-harness install-skills --client codex       # 也支持其他客户端目录
```

初始化后需要完成一次**作者说明确认**：编辑作者资料文件（默认 `author-profile.md`），写明目标读者、表达偏好、可用的个人经历和禁止的表达，然后亲自执行：

```bash
content-harness confirm-author
```

## 四、写一篇文章的完整流程

日常使用中你主要做三件事：说清想写什么、确认方向、审阅成稿。以下是背后的完整链路（大部分由 AI 执行，标注“**你执行**”的需要你在终端亲自确认）：

1. **开始**：AI 执行 `new` 创建 run，编号为日期加 slug。
2. **整理依据**：AI 保存 idea、sources（来源）、claims（事实主张）、brief（写作方向说明），每步用 `check --artifact` 登记。
3. **确认方向**（**你执行**）：审阅 brief 后执行 `approve <run-id> brief`，输入屏幕显示的哈希指纹。
4. **选风格**：AI 执行 `style` 编译风格说明。三种内置选择：正常表达（neutral / natural-human-zh）、公众号高传播（wechat-high-engagement）、高传播加去 AI 味。
5. **写作**：AI 依次完成 outline（提纲）、draft（初稿）、manuscript（成稿）、style-report（风格检查报告）。
6. **评审**：AI 完成 fact-review（事实检查）和 editorial-review（编辑检查）。遇到高风险事实或需认定为你亲历的内容，会请你执行 `verify-claim`（**你执行**）。
7. **配图**：需要图时生成 visual-plan 和 visual-assets；不需要时写明原因。
8. **打包**：AI 执行 `package <run-id> --titles titles.txt --summary summary.txt`。
9. **最终确认**（**你执行**）：审阅正文、标题、摘要、图片后执行 `approve <run-id> publish`。
10. **导出**：AI 执行 `export`，文章包保存到你配置的成品目录。

成品目录结构：

```text
成品目录/文章编号/
├── article.md     正文
├── titles.txt     候选标题
├── summary.txt    摘要
├── sources.yaml   来源记录
├── images.yaml    图片说明
└── assets/        配图（需要时才有）
```

不懂命令时，把[上手指南](getting-started.md#从一个想法到一篇文章)里的提示词直接发给 AI 即可，AI 会给你填好实际编号的确认命令。

## 五、命令速查

命令在**内容项目**中运行（不是源码目录），业务命令输出 `schema_version: 1` 的 JSON。全局参数 `--project <路径>` 放在子命令前。

### 环境与项目

| 命令 | 作用 |
|---|---|
| `version` / `doctor` | 查看版本 / 检查环境 |
| `init . --preset wiki` | 初始化写作项目配置 |
| `configure --output-dir ... --read-root ... --dedupe-root ... --scenario ...` | 设置成品位置、资料与查重目录、默认场景 |
| `install-skills --client <名称>` | 安装 13 个 Skills 到客户端目录 |
| `confirm-author` | **人工**确认作者资料 |

### 写作过程（通常由 AI 执行）

| 命令 | 作用 |
|---|---|
| `new` | 创建一篇文章的 run |
| `status <run-id> --json` | 看写到哪、哪些检查需要重做 |
| `resume <run-id> --json` | 从磁盘恢复进度（恢复状态，续写仍由 AI 完成） |
| `put <run-id> <资产> --from 文件 --expected-hash ...` | 安全写入资产，防止覆盖手改 |
| `check <run-id> --artifact <资产>` | 登记资产、跑确定性门禁检查 |
| `invalidate <run-id> <资产> --reason ...` | 主动作废某个资产 |
| `style <run-id> [--reset]` | 编译或重置风格说明 |
| `package` / `export` | 创建发布包 / 导出到成品目录 |
| `archive` / `restore` | 归档 / 恢复 run |

### 需要你亲自确认的命令

| 命令 | 你审阅的内容 |
|---|---|
| `confirm-author` | 作者资料是否真实、表达边界是否合适 |
| `approve <run-id> brief` | 写作方向和范围 |
| `verify-claim <run-id> <claim-id>` | 需人工核验的事实或亲历 |
| `approve <run-id> publish` | 最终正文、标题、摘要、图片 |
| `style-promote <run-id> <lesson-id>` | 是否把候选偏好写入长期风格记忆 |
| `style-rollback <scope> <version>` | 是否恢复旧版本风格记忆 |

这些命令在交互终端执行，按提示输入当前哈希指纹，AI 不代你执行。

## 六、让工具越来越懂你：风格反馈

手工改过成稿后，希望形成长期规则时：

1. **在重新登记手改稿之前**，让 AI 执行 `style-feedback <run-id> --artifact manuscript --scope scenario --reason '你的理由'`，保存修改前后差异。
2. AI 整理候选规则，给出应该改和不应该改的例子。
3. 你审阅后亲自执行 `style-promote`，规则才进入长期记忆并用于以后的文章。

scope 三档：`run` 只记本次，`scenario` 归到内容场景（推荐），`author` 作者级偏好（适用面广，谨慎确认）。只是临时调整时直接告诉 AI“这次不要记为长期偏好”即可。

## 七、中断恢复与手工修改

- **中途退出**：在同一项目里对 AI 说“继续上次那篇文章，先用 resume 检查状态”。工具会从磁盘重建进度，不会重新创建。
- **自己改了文件**：告诉 AI“我手工改过成稿，请先读取最新文件，保留我的修改后继续”。手改文件变为 in_progress、下游变为 stale，`check` 后重新登记；哈希不匹配时 `put` 会拒绝覆盖你的修改。
- **改稿后的审批**：审批绑定哈希和 revision，改稿后即使恢复旧内容也需重新审批。

## 八、常见错误速查

| 错误码 | 下一步 |
|---|---|
| AUTHOR_CONFIRMATION_REQUIRED | 编辑作者资料，执行 confirm-author |
| DEPENDENCY_BLOCKED / GATE_BLOCKED | 看 status 的 blocked，处理上游资产或审批 |
| CONFLICT_EXTERNAL_EDIT | 保留人工文件，重新读取并合并 |
| CLAIM_HUMAN_REQUIRED | 人工核验该 claim（verify-claim），再 check |
| REVIEW_INPUT_CHANGED | 重做评审并绑定最新输入哈希 |
| STYLE_FACT_DRIFT | 核对数字、引文、限定词；事实纠错从 claims/draft 返工 |
| EXPORT_CONFLICT | 保留原输出，改用新 run 或新输出目录 |
| RUN_LOCKED | 等另一进程完成，进程退出后锁自动释放 |
| WORKFLOW_CHANGED | 恢复该 run 创建时的 workflow.yaml |

更多返工、归档与恢复细节见[操作与排错](usage.md)。

## 九、升级

```bash
uv tool upgrade content-harness
content-harness version
```

升级后在内容项目中重新检查 Skills；新旧内容不同会触发冲突保护，先备份属于本项目的 13 个 Skill 文件夹再合并。已有 `project.yaml` 和文章保持原位，用 `configure` 调整即可，无需重复 `init`。

## 阅读导航

| 你想做什么 | 看这里 |
|---|---|
| 不懂命令，想完成第一篇文章（含可复制提示词） | [新手上手指南](getting-started.md) |
| 设置资料、成品目录，接入 LLM Wiki | [目录与知识库设置](wiki-integration.md) |
| 逐条理解命令 | [命令白话手册](commands.md) |
| 排查返工、冲突与恢复问题 | [操作与排错](usage.md) |
| 修改工具代码、跑测试、构建安装包 | [开发者说明](development.md) |
| 了解资产依赖 DAG 与实现边界 | [架构说明](architecture.md) |
