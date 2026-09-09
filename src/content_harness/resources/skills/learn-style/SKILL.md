---
name: learn-style
description: Content Harness 用户修改措辞、拒绝某种表达或希望沉淀场景偏好时使用。
---

# learn-style

输入：已登记版本、当前人工修改、反馈理由、style-report 和现有记忆。
场景从当前 run 的 scenario 读取，旧 run 无此字段才回退 workflow。不要根据文章话题自动更换场景或将局部偏好晋升为全局规则。
1. 在 check 登记手改稿之前运行 style-feedback；默认 scope=run，只有明确属于长期作者或场景偏好时才建议 author/scenario。
2. 在返回的候选文件中填写 proposed_rule、eval_proposal；对于模型/热点/平台变化相关规则填写 review_after。
3. eval_proposal 至少给出一个应改示例和一个不应改示例，说明事实保持条件。单篇临时改动不得推断为作者永久人设。
4. 展示候选 diff、规则、作用域和例子。长期晋升由用户执行 style-promote；Agent 不能自行调用。回退由用户执行 style-rollback。
输出：candidate lesson。完成标准是证据与规则可审阅；保存候选并不表示已学会或已验证有效。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
