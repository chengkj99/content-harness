# 开发者说明

本页面向修改 Content Harness 源码的人。只想写文章，请看 [新手指南](getting-started.md)。

## 安装与检查

```bash
git clone https://github.com/chengkj99/content-harness.git
cd content-harness
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run python scripts/export_schemas.py --check
uv build
```

修改模型后，运行 `uv run python scripts/export_schemas.py` 重新生成 schemas，再做一致性检查。依赖和包版本变更后更新 uv.lock；CI 使用锁定版本。

源码位于 src/content_harness，工作流、Skills 和风格资源位于其中的 resources，随 wheel 分发。workflow 是依赖关系的唯一可执行来源，不能只改文档图而不核对工作流。

## 文档图验证

架构文档使用 Mermaid。节点 ID 避免使用 style 等语法词，显示文字可以通过独立的标签表达。语法参考 [Mermaid 流程图文档](https://mermaid.js.org/syntax/flowchart.html)。GitHub 支持的渲染版本可能变化，见 [GitHub 图表说明](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)。

可选脚本 scripts/check_diagrams.mjs 使用真实解析器和浏览器渲染所有文档 Mermaid 块，同时确认旧错误能够复现。需要 Node.js、Playwright/Chromium 及本地 Mermaid UMD 文件；这些不是使用 Python CLI 的前提。

```bash
HARNESS_MERMAID_BUNDLE='/path/to/mermaid.min.js' node scripts/check_diagrams.mjs
```

脚本在本地空白页加载依赖，并禁用网络请求，不将 README 或 docs 发送给在线渲染服务。Playwright 不在默认解析路径时可设置 HARNESS_PLAYWRIGHT_MODULE；使用已有 Chrome 时可设置 HARNESS_CHROME。本次验证使用 Mermaid 11.4.1，不把它声称为 GitHub 当前部署的版本。

## 安装包验证

构建后在独立环境安装生成的 wheel，再执行 scripts/smoke_install.py。它在临时内容项目中检查版本、workflow、初始化、doctor、13 个 Skills 与作者确认门禁。不要只依赖源码目录中的成功运行。

CI 配置覆盖 Python 3.11/3.12/3.13。发布记录必须分别报告本地测试、独立安装、远端 CI 和真实模型试用的实际结果，不互相代替。已有的机制测试不证明文章质量或传播效果。
