---
name: content-harness
description: 用户要使用 Content Harness 写文章、开始任务、处理返工或继续中断任务时使用。
---

# content-harness

1. 读取项目 AGENTS.md 和 project.yaml 的 policy_files；仅读取 read_roots、dedupe_roots 范围内与本篇相关的材料。首次使用先问素材、旧稿和成品分别放在哪里，不根据仓库名称猜目录。解释拟写入位置，得到用户选择后 init；已有项目先 configure 查看配置，按明确需求更新，勿重新初始化。
2. 新任务先用 new 创建 run，再把用户原始想法完整保存为 idea；已有 run 执行 status --json。资产格式与命令见 [契约](references/contract.md)。
3. 只从 ready 选一个资产，读取其生产 Skill；human_gates 非空则展示具体文稿摘要、哈希与命令并停止。
4. 每完成一种资产，执行 check --artifact，再重新读取 status。不要凭对话推测状态；遇 stale 只处理受影响资产。
5. publish-package 完成后等待用户审批；export 成功表示本地交付完成，不表示公众号已发布。

## 面向创作者的交互

- 用户不需要理解 JSON、资产 ID 或哈希。平时用“选题卡、提纲、初稿、成稿”说明目前进度、改了什么、下一步需要什么。
- 读取配置的 author_sources 指定的作者资料，不假定文件名；缺少作者确认时，先解释确认内容，再给出用户可直接复制的完整命令。审批命令必须替换真实项目路径与 run-id，不能把 `<run-id>` 留给新手猜。
- 只在必须用户决策/审批或输入不足时停下。用户在聊天中说“同意”不等于终端审批，不可代为输入确认。
- 用户需要区分读书笔记、教程等偏好时，解释 `new --scenario` 只选择风格记忆，不会切换成新的内容生产流程。没有明确选择则沿用项目默认场景。
- 导出前核对实际目标与目录；默认执行 `export <run-id>` 使用项目 default_target，不强制 wechat。新目标不是新的平台发布接口。不得自行修改 Wiki 索引或摄入知识库。


遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
