---
name: learn-style
description: Content Harness 用户修改措辞、拒绝某种表达或希望沉淀场景偏好时使用。
---

# learn-style

输入：已登记版本、当前人工修改、反馈理由、style-report 和现有记忆。
场景从当前 run 的 scenario 读取，旧 run 无此字段才回退 workflow。不要根据文章话题自动更换场景或将局部偏好晋升为全局规则。
1. 用户已经手改时，在 check 登记手改稿之前运行 style-feedback；只有拒稿理由或对标样稿时运行 style-note。默认 scope=run，只有明确属于长期作者或场景偏好时才建议 author/scenario。
2. 在返回的候选文件中填写 proposed_rule、eval_proposal；对于模型/热点/平台变化相关规则填写 review_after。
3. eval_proposal 至少给出一个应改示例和一个不应改示例，说明事实保持条件。单篇临时改动不得推断为作者永久人设。
4. 展示候选 diff、规则、作用域和例子。在聊天中取得用户针对该候选的明确确认后，Agent 调用 style-promote 的 --chat-confirmed 模式；回退同样先展示目标版本并确认，再调用 style-rollback。
输出：candidate lesson。完成标准是证据与规则可审阅；保存候选并不表示已学会或已验证有效。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

## 手改分析顺序

- 用户改的是发布包 article.md 时，使用 `style-feedback --artifact publish-package`；基线已被登记成中间版时，用 `--before-hash` 明确选择原始登记快照。先核对基线，不能默认当前 manuscript 就是首版。工具会快照保存手改输入，不登记、不改稿、不代审批。
- 逐项区分表达偏好、观点新增、事实/承诺强度变化、笔误，以及原样保留的结构。未改部分只能说明本轮未动，不能推断永远认可。
- 对表达偏好提炼“适用场景 + 应改例 + 不应改例”。学习动机和节奏，不复制口头禅、病句、绝对化标题或一篇文章的专属故事。
- 删除泛化的免责段，不等于取消事实限制；可在内部审校保留限制，正文是否保留取决于读者误解或照做的实际风险。新增观点返回 Claims/Brief 审核，不能由风格学习偷偷晋升为事实。
- 用户明确要求优化项目配置时，可直接更新项目表达样本和场景配置，注明依据、适用范围及单篇样本的局限；不冒充已晋升的 style-memory，也不把个人偏好写进通用框架。

遇到缺少输入、stale 依赖或人类审批要求时，展示待确认的具体内容并在聊天中等待用户明确回复。确认后，Agent 可用对应命令的 --chat-confirmed 模式记录决定，传入审阅时的哈希；approve 还要传入资产 revision。内容变化时重新请求确认；不得自行决定或把一般性的“继续”当成确认。
