# 命令白话手册

这些命令大部分由 AI 帮你执行。你只需要知道它们的作用，遇到确认或问题时能作出判断。第一次写文章请先看 [上手指南](getting-started.md)，不用从头背命令。

## 先读懂命令里的符号

| 写法 | 含义 |
|---|---|
| content-harness | 让电脑调用这个工具 |
| status、resume 等词 | 这次要做什么 |
| `<run-id>` | 要替换成实际文章编号，不包含尖括号；让 AI 帮你填完整 |
| `.` | 当前项目文件夹，不是电脑的任意目录 |
| `--json` | 让结果采用 AI 更容易读取的结构化格式，不会生成另一篇文章 |
| `--` 后面的词 | 补充设置，例如保存位置、使用什么风格 |
| 行末的 `\` | 命令写不下时换行接着写，仍是一条命令；不熟悉时让 AI 给单行版 |

run 可以理解为“一篇文章的一次工作记录”。它有自己的编号、稿件、修改记录和检查结果。状态里的 stale 表示“上游改过，这个结果需要重新处理”，不表示文件被删除。

命令要在内容项目中运行，不一定是在 Content Harness 的源码目录。分不清当前目录时，让 AI 明确显示路径；也可以由 AI 使用全局参数 `content-harness --project '项目路径' ...`。

## 你列出的命令，分别是什么意思

| 命令 | 白话意思 | 谁通常执行 | 会改什么 |
|---|---|---|---|
| `content-harness status <run-id> --json` | 看这篇写到哪，哪些检查需要重做 | AI | 更新发现文件变化的状态记录，不改文章正文 |
| `content-harness resume <run-id> --json` | 从磁盘恢复进度，告诉 AI 下一步 | AI | 重建/更新状态，不会自己续写正文 |
| `content-harness style <run-id> --reset` | 关闭额外风格，恢复作者资料加默认表达 | AI，按你的要求 | 重编风格说明，使相关下游稿件/检查失效；不删除旧稿、不清空长期记忆 |
| `content-harness init . --preset wiki` | 在当前知识库中准备工作区 | 首次准备时由 AI 帮助 | 新建工具配置和必要模板，不生成文章；已有配置会拒绝重复初始化 |
| `content-harness install-skills --client codex` | 把写作操作指引放到 Codex 可发现的目录 | AI | 安装本项目的 13 个 Skills；不是安装 Codex 本身 |
| `content-harness style-feedback ...` | 记录你改了什么、为什么改，为以后积累偏好 | AI | 新建反馈候选，不自动更改长期风格 |

特别注意：resume 的作用是恢复进度，“真正接着写”仍由 AI 完成。你可以说：“请继续这篇文章，先用 resume 检查状态，再执行下一步。”

## 风格反馈的长命令怎么读

```bash
content-harness style-feedback <run-id> --artifact manuscript --scope scenario --reason '结尾要给出具体动作'
```

- artifact manuscript：比较的是你手工修改的成稿。
- scope scenario：建议把经验归到这类内容场景，例如读书笔记；不是立刻应用到所有文章。
- reason：你为什么这样改，是给 AI 理解的具体理由。

需要在重新登记手改稿前执行，否则比较基线会被更新。候选规则由 AI 整理，你确认后才执行 style-promote。scope run 只记本次；author 表示作者级偏好，适用范围更广，应谨慎确认。

## 设置目录的命令

```bash
content-harness configure --output-dir '知识库/我的文章' --target library
content-harness configure --read-root '素材' --read-root '笔记' --dedupe-root '旧文章'
content-harness configure --scenario book-notes
```

分别表示设置成品位置、资料与查重位置、新文章默认的风格分组。带空格或模板变量的路径应放在引号中。配置变化不移动旧文件；完整说明见 [目录设置](wiki-integration.md)。

## 哪些命令需要你亲自确认

| 命令 | 你需要审阅的东西 |
|---|---|
| `confirm-author` | 作者资料是否真实、表达边界是否合适 |
| `approve <run-id> brief` | 写作方向和范围 |
| `verify-claim <run-id> <claim-id>` | 需要人工核验的具体事实或亲历 |
| `approve <run-id> publish` | 最终正文、标题、摘要、图片与交付 |
| `style-promote <run-id> <lesson-id>` | 是否把候选偏好用于以后的作者/场景表达 |
| `style-rollback ...` | 是否恢复某个旧版本的风格记忆 |

AI 给你填好实际编号的命令，你读过对应内容后在交互终端执行，按提示输入当前哈希（版本指纹）。AI 不代你执行。这是当前工具的确认方式，不是“在聊天里答应过，以后就全部自动通过”。

## 那四条 uv 命令是写文章用的吗

不是。它们用于维护工具本身，普通创作者可以跳过。

| 命令 | 给维护者的作用 |
|---|---|
| `uv run pytest` | 运行自动化测试，检查工具改动是否破坏已有行为 |
| `uv run ruff check .` | 检查 Python 代码规范和部分错误 |
| `uv run python scripts/export_schemas.py --check` | 检查数据格式说明是否与代码一致 |
| `uv build` | 把软件打成可安装的包，不是把文章发布到平台 |

uv run 表示在该项目的 Python 环境里运行后面的程序。这些开发命令应该在 Content Harness 源码目录执行；不需要在每个文章目录执行。详细步骤在 [开发者说明](development.md)。

## 升级工具与已有项目

从 GitHub 安装的用户，可以让 AI 帮助运行：

```bash
uv tool upgrade content-harness
content-harness version
```

随后在内容项目中检查 Skills。新版 Skills 与旧版不同会触发冲突保护；先备份安装目录内属于 Content Harness 的 13 个 Skill 文件夹，检查是否有你的自定义修改，再重新安装或合并。不要为了升级而删除整个 .agents/skills 或其他客户端的 Skills 目录。

现有 project.yaml 和文章保持原位。用 configure 修改需要调整的设置即可；无需重复 init。新版本读取旧 run 时兼容缺失的场景字段，仍使用它原来的工作流场景。更新后生成的新状态应继续用新版工具读取。
