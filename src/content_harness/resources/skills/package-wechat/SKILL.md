---
name: package-wechat
description: Content Harness 成稿、风格和配图均通过检查，需要生成公众号发布包时使用。
---

# package-wechat

输入：已评审 manuscript、brief、两类 review、style-report、visual-assets。
1. 生成候选标题 titles.txt 和摘要 summary.txt。标题只能兑现正文，摘要不新增事实或收益承诺。
2. 调用 package --titles <file> --summary <file>；CLI 保留评审正文，删除内部 claim 标记，并按已登记计划的位置插入本地图片、复制来源。
3. 已有发布包不会自动覆盖；返工先把旧包移到 run 内的唯一备份目录，再重新 package。
4. check --gate publish 后展示标题、摘要、正文、图清单、输出位置与哈希，等用户 approve publish。
5. 用户批准后 export。M1 只交付本地发布包，不操作公众号接口，不声称已发布。
输出：publish-package。完成标准：当前内容通过检查并经用户审批后成功导出。

操作前读取 [资产与 CLI 契约](../content-harness/references/contract.md)。

遇到缺少输入、stale 依赖或人类审批要求时，报告阻塞及具体下一步。Agent 不得自行执行 approve、confirm-author、verify-claim、style-promote、style-rollback。
