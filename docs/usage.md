# 操作指南

用户主要与 Agent 对话；以下命令用于检查过程和接管任务。所有业务命令输出带 schema_version: 1 的 JSON。全局参数 `--project <path>` 放在子命令前。

## 完整链路

1. init 创建配置，编辑 author-profile.md，由用户 confirm-author。
2. new 创建日期加 slug 的 run；同一天同名会报冲突。
3. Agent 保存 idea、sources、claims、brief，每步 check --artifact。
4. 用户 approve brief，Agent 执行 style 编译默认或所选风格。
5. Agent 完成 outline、draft、manuscript、style-report、fact-review、editorial-review。
6. 评审通过后生成 visual-plan、visual-assets；无图时写明原因。
7. `package <run-id> --titles titles.txt --summary summary.txt` 创建包。
8. 用户 approve publish，再 export 得到本地文章包。

各资产格式见 [Skill 契约](../src/content_harness/resources/skills/content-harness/references/contract.md)。draft 同时依赖 brief、outline、claims、style-spec：分别确定读者与边界、结构、事实、表达。

## 安全写入与继续

```bash
content-harness put <run-id> idea --from idea.md --expected-hash missing
content-harness check <run-id> --artifact idea
content-harness resume <run-id> --json
```

已有资产的 expected-hash 从 status 的 content_hash 取；这是文件树哈希，不能用单文件 sha256sum 替代。哈希不匹配不会覆盖，应重新读取并合并。

status 会扫描文件并写入“发现变化”事件，但不改文章。手改文件成为 in_progress，下游成为 stale；check 后才重新登记。review 的 input_hashes 必须是当前依赖，旧报告不能原样复用。

style-feedback 在登记人工改稿之前执行，否则最新快照会成为新比较基线。

## 错误处理

| 错误 | 下一步 |
|---|---|
| AUTHOR_CONFIRMATION_REQUIRED | 编辑作者资料，用户 confirm-author |
| DEPENDENCY_BLOCKED / GATE_BLOCKED | 看 status.blocked，处理上游或审批 |
| CONFLICT_EXTERNAL_EDIT | 保留人工文件，重新读取并合并 |
| CLAIM_HUMAN_REQUIRED | 用户核验具体 claim，再 check |
| REVIEW_INPUT_CHANGED | 重做评审并绑定最新输入哈希 |
| STYLE_FACT_DRIFT | 核对数字、引文、限定词，事实纠错从 claims/draft 返工 |
| EXPORT_CONFLICT | 保留原输出，使用新 run 或新配置目标 |
| RUN_LOCKED | 等另一进程完成；进程退出后锁自动释放 |
| WORKFLOW_CHANGED | 恢复该 run 创建时的 workflow.yaml |

## 包返工、归档与恢复

重新 package 前，把旧 artifacts/60-publish-package 移到 run 内唯一命名的备份目录。已有外部导出永不覆盖，新版文章使用新 run 或新输出目录。

```bash
content-harness archive <run-id>
content-harness restore <run-id>
```

manifest 损坏时 resume 从 transitions.jsonl 自动重建。末尾半条事件先保存 journal-tail 再修复；完整损坏事件报错，不猜测历史。不要手工修改日志或快照。

## 风格回滚

```bash
content-harness style-rollback scenario 0 --scenario wechat-longform
```

用户确认后，把旧规则恢复为新版本。eval_proposal 是待验证的案例说明，不表示模型评估已经运行；与模型或平台有关的过期规则先重新验证。
