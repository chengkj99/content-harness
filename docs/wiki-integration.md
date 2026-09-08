# Wiki 接入

在 kj-llm-wiki 或其他 Wiki 中，Content Harness 是独立安装的工具。核心不包含个人路径或私有作者风格。

先阅读该 Wiki 的 AGENTS.md、SCHEMA.md 和内容流程规定，再在根目录执行：

```bash
content-harness init . --preset wiki
content-harness install-skills --client codex
```

默认材料根为 raw、wiki，去重目录为 raw/studio/funnel/formatted/wechat。按实际仓库收窄 read_roots、补充 policy_files；作者资料在本项目填写和确认。

```yaml
exports:
  wechat:
    directory: raw/studio/funnel/formatted/wechat/{run_id}
```

导出是一个完整发布包目录。article.md 为成稿，其余为标题、摘要、来源和图片。M1 采用整体目录交付，与早期设计的单个 `{date}-{slug}.md` 模式不同；需要兼容旧工具时，可在人审后额外复制成稿，工具本身不会自动改动旧内容。

`.content-harness/.gitignore` 默认忽略 run、作者资料、风格记忆和归档。project.yaml 可在审阅后单独提交。需要跟踪工作资产时，先核对隐私、版权和项目规则；工具不会自动暂存或推送 Wiki。

scenario=wechat-longform 的反馈不会进入 technical-tutorial 或公共 Style Pack。新偏好只在下次编译 style 时使用，旧稿保留快照。

本次项目实现没有自动初始化或修改任何实际 Wiki；用户在选定 Wiki 中执行上述命令即可接入。
