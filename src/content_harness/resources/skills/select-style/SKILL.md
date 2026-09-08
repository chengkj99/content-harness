---
name: select-style
description: Content Harness 需要设置公众号高传播风格、去 AI 味、默认风格或切换风格时使用。
---

# select-style

输入：已批准 brief、用户选择、project profile 与项目风格记忆。
1. 按需执行 style；高传播用 --use wechat-high-engagement，去 AI 味用 --use natural-human-zh，可组合。未选择时不自动打开任何附加风格。
2. style 命令确定性地编译 style-spec，内含完整规则与创建时的记忆快照。不要手改 style-spec。
3. 检查 style-spec：Author → Scene → Polish；强度不改变事实约束。切换用 style --reset 或新选择，按 status 返回的 stale 返工。
4. 遇已有手改 style-spec 导致冲突，先保留手改内容并报告，不覆盖。
输出：style-spec。完成标准是已登记且能从其自身还原所有风格规则和版本。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
