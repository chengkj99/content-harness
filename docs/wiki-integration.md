# 目录与 LLM Wiki 设置

Content Harness 可以在普通写作文件夹、Git 仓库、Obsidian 等工具管理的文件夹，以及 LLM Wiki 仓库中使用。这里的 LLM Wiki 指用文件组织资料和知识的仓库，不指某个特定作者的项目。

## 不懂配置文件，也可以先告诉 AI

```text
请把当前文件夹作为 Content Harness 写作项目。
资料从“原始资料/读书笔记”和“素材”读取。
已有文章在“知识库/旧文章”，需要检查是否重复。
成品保存到“知识库/我的文章”，每篇一个独立文件夹。
先阅读项目已有规则，保留所有旧文件。
请初始化或调整配置，完成后告诉我实际读取和保存的位置。
```

AI 可以代为执行 init 或 configure。项目已有 AGENTS.md、SCHEMA.md 等规则时应先读取；没有这些文件也能使用，不需要为满足预设格式而新建一个知识库。

这里的“沉淀”是把文章和相关材料保存到你指定的位置。自动改写知识库目录索引、合并已有页面、生成双向链接或执行知识摄入流程，不在当前导出功能内；如需这些动作，应另行说明，并遵守你的知识库规则。

## 哪些位置可以改

| 你关心的东西 | 配置项 | 修改后的行为 |
|---|---|---|
| 素材从哪来 | read_roots | AI 查阅的资料根目录 |
| 去哪里看是否写过 | dedupe_roots | AI 检查重复主题的旧稿目录 |
| 遵守哪些项目规定 | policy_files | AI 需要读取的规则文件 |
| 作者说明放哪里 | author_sources | 可以引用项目内已有的一份作者资料文件 |
| 成品保存到哪里 | exports | 一个或多个命名目标，每个目标一个目录模板 |
| 默认用哪个目标 | default_target | 不指定目标时使用它 |
| 哪类文章积累同一套偏好 | style.default_scenario | 新文章采用的默认风格场景 |
| 哪些样稿定义表达好坏 | style.reference_files | 项目内正反样稿及说明，不作为新文章事实 |
| 每个场景默认用什么风格 | style.scenarios | 为个人随笔、教程等分别设置 Scene/Polish |

这些设置约束 Content Harness 及其 Skills 的约定行为，不是对宿主 AI 的文件系统权限隔离。工具自身导出会检查实际路径和冲突。

过程状态固定保存在 .content-harness 中，这是隐藏的工具工作目录，不是成品目录。保留这个统一位置有利于中断恢复；读者需要看的文章目录由你选择。

## 三种常见安排

下面只是可选示例，不是必须遵守的命名规则。

| 项目 | 资料目录示例 | 成品目录示例 |
|---|---|---|
| 普通写作文件夹 | 素材、笔记 | 成品文章 |
| 英文目录的知识库 | raw/notes、wiki/research | wiki/articles |
| 中文目录的知识库 | 原始资料、知识库/读书笔记 | 知识库/我的文章 |

## 已熟悉命令时这样配置

首次创建：

```bash
content-harness init . --preset wiki --output-dir '知识库/我的文章' --target library --read-root '原始资料' --dedupe-root '知识库/旧文章'
```

preset wiki 只表示在已有知识库中准备写作环境：不猜测资料根，不使用个人专属输出目录。未指定成品位置时默认 content/<文章编号>/；你可以随时改。普通文件夹无需 preset wiki。

调整已有项目：

```bash
content-harness configure --output-dir 'wiki/articles' --target library
content-harness configure --read-root 'raw/notes' --read-root 'wiki/research' --dedupe-root 'wiki/articles'
content-harness configure --author-file '关于作者.md' --scenario book-notes
```

同一命令里重复 read-root 或 dedupe-root 表示多个目录；提供新列表时替换原列表，不是偷偷追加。只改输出目录不会自动改变资料或查重目录，需要时一并设置。author-file 应指向已经存在的文件；若作者内容变化，需重新确认。执行 configure 不带参数可查看配置。

一个配置片段：

```yaml
author_sources:
  - 关于作者.md
read_roots:
  - 原始资料
dedupe_roots:
  - 知识库/我的文章
default_target: library
exports:
  library:
    directory: 知识库/我的文章/{run_id}
  blog:
    directory: 博客待发布/{date}/{slug}
style:
  default_scenario: book-notes
  default_scene: null
  default_polish: []
  allow_run_override: true
  reference_files: []
  scenarios:
    personal-essay:
      scene: personal-narrative-zh
      polish:
        - natural-human-zh
```

这是用于解释的片段，不要用它覆盖整个 project.yaml。建议让 AI 通过 configure 更新需要的字段，保留其他设置。

## 成品命名、不同目标与不同场景

output-dir 不含模板变量时，工具会在目录后加 /{run_id}，让每篇文章有独立文件夹。模板支持：

- {run_id}：完整文章编号，例如 2026-09-09-material-to-action。
- {date}：文章任务创建日期，不是导出当天的日期。
- {slug}：文章编号中的短名称，例如 material-to-action。
- {scenario}：本篇固定的风格场景，例如 book-notes。

命令中带花括号、空格或中文时，用引号包裹整条路径。

```bash
content-harness configure --output-dir '成品/{scenario}/{date}/{slug}' --target library
```

配置后省略目标会使用默认位置；需要另一份复制时，可以显式选择已配置目标：

```bash
content-harness export <run-id>
content-harness export <run-id> --target blog
```

library、blog 只是目标的短名称，不代表已经连接某个平台。输出仍然是 article.md、标题、摘要、来源记录和必要图片组成的文件夹。

场景是风格偏好的分组，与成品目标分开。可以让 AI 建立 newsletter、product-notes 等场景；同一长文流程可以分别积累偏好。新文章可以使用 new --scenario 覆盖项目默认值；项目默认场景改变后，已有文章仍保留创建时的场景。自定义场景不会增加新的平台适配流程。

场景还可以绑定默认风格栈。个人随笔适合 personal-narrative-zh，教程可按需使用 wechat-high-engagement，两者都可叠加 natural-human-zh。reference_files 使用项目内显式文件；Content Harness 会把内容和哈希固化到 voice-contract，参考文件变化后提示重做，不会把样稿事实登记成 Claims。

## 已有文件和旧版本怎么办

改变配置不搬动旧稿、不改写旧文章。已有 run 下一次 export 使用当前输出配置，已经导出的旧文件保留原位。目标有不同内容时会报冲突；选择新目录或新文章编号，而不是让工具覆盖旧文件。

升级前已经配置好的目录会被保留，即使它使用旧版较长的目录结构。需要简化时执行 configure，不必重新 init，也不要删除 .content-harness。

目录必须在所选项目中，不能通过 ..、绝对路径或符号链接跳到项目之外。用户明确配置的 wiki/ 子目录可以导出；Git 元数据、工具状态和 AI 客户端配置目录仍不可作为文章目标。若要写到另一个仓库，先把那个仓库选为写作项目。

工具不会自动提交或推送你的文章。过程资产、作者资料和风格记忆默认按隐藏工作目录的规则忽略；若把作者资料改到其他位置，应自行核对该仓库的跟踪规则。
