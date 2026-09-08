---
name: content-harness
description: 用户要使用 Content Harness 写文章、开始任务、处理返工或继续中断任务时使用。
---

# content-harness

1. 读取项目 AGENTS.md 和 project.yaml 的 policy_files；仅读取 read_roots、dedupe_roots 范围内与本篇相关的材料。缺少项目先运行 init，作者确认缺失时显示 confirm-author 给用户。
2. 新任务先用 new 创建 run，再把用户原始想法完整保存为 idea；已有 run 执行 status --json。资产格式与命令见 [契约](references/contract.md)。
3. 只从 ready 选一个资产，读取其生产 Skill；human_gates 非空则展示具体文稿摘要、哈希与命令并停止。
4. 每完成一种资产，执行 check --artifact，再重新读取 status。不要凭对话推测状态；遇 stale 只处理受影响资产。
5. publish-package 完成后等待用户审批；export 成功表示本地交付完成，不表示公众号已发布。



遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
