# 项目约定

本项目独立实现 Content Harness，不依赖其他私有 skill 或个人知识库。

- 使用 Python 3.11+、Typer、Pydantic、YAML；通过 `uv sync --extra dev` 安装。
- 修改状态、审批、路径边界时补充回归测试，运行 `uv run pytest` 和 `uv run ruff check .`。
- workflow 是 DAG 的唯一来源；Skills 通过 CLI JSON 状态工作。
- 人工审批属于运行时用户操作，Agent 不得自行调用 approve、confirm-author、verify-claim、style-promote 或 style-rollback。
- 不包含个人路径、凭据、私有内容；文档和 Skills 使用中文。
- 不将 CLI 测试冒充真实模型、跨客户端或真实文章试用结果。
