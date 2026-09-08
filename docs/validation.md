# 验证记录

日期：2026-09-08。版本：0.1.0。当前发布范围是 M0/M1 初始实现，不声称原设计的 M2/M3 完成。

## 自动化验收

本地 macOS、Python 3.11.15：67 项测试通过（6.55 秒）；Ruff 检查、Pydantic Schema 一致性检查通过。wheel 与 sdist 构建成功；在独立临时环境安装 wheel，验证 13 个 Skills、workflow、init、doctor 与作者确认门禁通过。用以下命令复现：

```bash
uv sync --locked --extra dev
uv run pytest
uv run ruff check .
uv run python scripts/export_schemas.py --check
uv build
```

测试覆盖：

- 合成文章从 idea 到发布包、审批、导出、重启后幂等重试；无图和静态 SVG 两条路径。
- draft 手改的精确 stale 范围、旧审批失效、改回原字节不复活审批。
- manifest 缺失/损坏/落后、事件提交后索引失败、末尾半条记录、完整损坏事件。
- run 锁互斥与释放、CAS 写入冲突、快照保留、workflow 固化及环检测。
- 缺少直接证据、高风险确认、旧评审输入、语义 blocker、事实标记覆盖。
- 数字、限定词、受保护词和 claim 标记变化的风格拦截。
- 作者/场景记忆隔离、候选不自动晋升、版本回滚、历史文章快照不变。
- 路径越界、符号链接、缺图、危险 SVG、无效链接、部分凭据特征和旧导出保护。
- CLI 实参、机器可读输出、非 TTY 人工操作拒绝、Skills 安装冲突、归档恢复。

所有内容夹具明确为合成数据。测试中的审批注入只存在于 tests，不提供运行时跳过审批的参数。没有调用真实模型或外部发布 API。

## 验证边界

| 项目 | 状态 |
|---|---|
| 本地自动化机制测试 | 67 passed |
| Ruff / Schema / 文档相对链接 | 通过 |
| wheel / sdist 构建 | 通过 |
| wheel 独立环境安装 | 通过，13 个 Skills、3 套风格 |
| Codex/Claude/Cursor 的 Skills 目录安装 | 自动化验证，非客户端行为认证 |
| 人工审批终端流程 | 自动化模拟，非身份认证 |
| 真实模型调研/写作/评审行为 | 未运行 |
| 10 篇真实文章试用 | 未运行 |
| 配对盲评与四周持续使用 | 未运行 |
| 公众号发布与 metrics | 未实现 |

剩余工作需要真实任务与用户参与，不能用合成测试替代。[24 项 behavior 任务](../evals/behavior/tasks.yaml)供下一阶段收集记录，均标为 not_run；通过本次机制测试不表示内容质量或传播效果已有提升。GitHub Actions 已配置 Python 3.11/3.12/3.13，远端执行状态以 Actions 实际记录为准。
