import functools
import json
import os
import shutil
import sys
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import ValidationError

from . import __version__, exporting, profiles, styles, workflows
from .gates import (
    claim_batch_hash,
    claim_hash,
    claim_verification_items,
    ledger,
    validate_artifact,
)
from .models import Approval, Feedback
from .state import Run
from .storage import (
    HarnessError,
    atomic_write,
    digest,
    files,
    identifier,
    lock,
    now,
    read_yaml,
    require,
    safe_path,
    tree_hash,
    yaml_bytes,
)

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Content Harness：本地内容资产、审阅、风格与恢复。所有结果可作为 JSON 读取。",
)
project_option = Path.cwd()


def emit(data):
    typer.echo(json.dumps({"schema_version": 1, "ok": True, **data}, ensure_ascii=False, indent=2))


def command(*args, **kwargs):
    def register(fn):
        @functools.wraps(fn)
        def wrapped(*a, **kw):
            try:
                return fn(*a, **kw)
            except (HarnessError, ValidationError, yaml.YAMLError, ValueError, OSError) as exc:
                code = exc.code if isinstance(exc, HarnessError) else "VALIDATION_ERROR"
                typer.echo(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "ok": False,
                            "error": {"code": code, "message": str(exc)},
                        },
                        ensure_ascii=False,
                    )
                )
                raise typer.Exit(1) from exc

        return app.command(*args, **kwargs)(wrapped)

    return register


@app.callback()
def setup(
    project: Annotated[Path | None, typer.Option(help="项目目录，默认从当前目录向上查找")] = None,
):
    global project_option
    project_option = project or Path.cwd()


def project():
    return profiles.project_root(project_option)


@contextmanager
def session(run_id, scan=True):
    identifier(run_id)
    root = project()
    profiles.profile(root)
    path = safe_path(root, ".content-harness/runs/" + run_id)
    require(path.is_dir(), "RUN_NOT_FOUND", run_id)
    with lock(path):
        run = Run(path)
        require(not run.state.archived, "RUN_ARCHIVED", run_id)
        if scan:
            run.scan()
            styles.scan_voice_contract(run, root)
        yield run, root


def human_confirm(subject, content_hash, chat_confirmed=False, expected_hash=None):
    if chat_confirmed:
        require(expected_hash == content_hash, "CONFLICT_EXTERNAL_EDIT", "确认对象已变化")
        return "human:agent-chat"
    require(is_tty(), "HUMAN_TTY_REQUIRED", "请用户在交互终端亲自执行此命令")
    typer.echo(subject)
    typer.echo("确认对象哈希: " + content_hash)
    answer = typer.prompt("确认后输入完整哈希；其他输入取消")
    require(answer == content_hash, "APPROVAL_CANCELLED", "哈希未确认")
    return "human:local-tty"


def is_tty():
    return sys.stdin.isatty()


@command()
def version():
    """显示版本。"""
    emit({"version": __version__})


@command()
def init(
    path: Annotated[Path, typer.Argument()] = Path("."),
    workflow: str = "wechat-longform",
    preset: str = "default",
    output_dir: str | None = None,
    target: str | None = None,
    read_root: Annotated[list[str] | None, typer.Option(help="允许读取的资料目录，可重复")] = None,
    dedupe_root: Annotated[
        list[str] | None, typer.Option(help="检查重复选题的目录，可重复")
    ] = None,
    author_file: str | None = None,
    scenario: str | None = None,
):
    """初始化写作文件夹；资料、成品目录可选，Wiki 不预设个人目录结构。"""
    workflows.load(workflow)
    require(preset in {"default", "wiki"}, "INVALID_PRESET", preset)
    result = profiles.init(
        path,
        workflow,
        preset,
        output_dir=output_dir,
        target=target,
        read_roots=read_root,
        dedupe_roots=dedupe_root,
        author_file=author_file,
        scenario=scenario,
    )
    emit(
        {
            "project": str(path.resolve()),
            "profile": result,
            "next": f"Edit {result['author_sources'][0]}, then confirm-author",
        }
    )


@command()
def configure(
    output_dir: str | None = None,
    target: str | None = None,
    read_root: Annotated[list[str] | None, typer.Option()] = None,
    dedupe_root: Annotated[list[str] | None, typer.Option()] = None,
    policy_file: Annotated[list[str] | None, typer.Option()] = None,
    author_file: str | None = None,
    scenario: str | None = None,
    style_reference: Annotated[list[str] | None, typer.Option()] = None,
    scene_style: str | None = None,
    polish_style: Annotated[list[str] | None, typer.Option()] = None,
    clear_read_roots: bool = False,
    clear_dedupe_roots: bool = False,
    clear_style_references: bool = False,
):
    """查看或调整项目设置；更新目录不移动旧稿，也不改已有文章的场景。"""
    require(
        not (read_root and clear_read_roots), "INVALID_ARGUMENT", "read-root or clear-read-roots"
    )
    require(
        not (dedupe_root and clear_dedupe_roots),
        "INVALID_ARGUMENT",
        "dedupe-root or clear-dedupe-roots",
    )
    require(
        not (style_reference and clear_style_references),
        "INVALID_ARGUMENT",
        "style-reference or clear-style-references",
    )
    for style_id in [scene_style, *(polish_style or [])]:
        if style_id:
            styles.pack(style_id)
    options = dict(
        output_dir=output_dir,
        target=target,
        read_roots=[] if clear_read_roots else read_root,
        dedupe_roots=[] if clear_dedupe_roots else dedupe_root,
        policy_files=policy_file,
        author_file=author_file,
        scenario=scenario,
        reference_files=[] if clear_style_references else style_reference,
        scene_style=scene_style,
        polish_styles=polish_style,
    )
    root = project()
    value = (
        profiles.configure(root, **options)
        if any(v is not None for v in options.values())
        else profiles.profile(root)
    )
    emit(
        {
            "profile": value,
            "note": "Directory changes apply to future exports; existing files stay where they are",
        }
    )


@command()
def confirm_author(
    chat_confirmed: bool = False, expected_hash: str | None = None, preview: bool = False
):
    """由用户确认作者资料；内容改变后需重新确认。"""
    root = project()
    content_hash = profiles.author_hash(root)
    if preview:
        emit({"subject": profiles.author_path(root).read_text(), "content_hash": content_hash})
        return
    actor = human_confirm(
        profiles.author_path(root).read_text(), content_hash, chat_confirmed, expected_hash
    )
    with lock(safe_path(root, ".content-harness")):
        require(
            profiles.author_hash(root) == content_hash, "CONFLICT_EXTERNAL_EDIT", "author profile"
        )
        atomic_write(
            safe_path(root, ".content-harness/author-confirmation.yaml"),
            yaml_bytes({"content_hash": content_hash, "at": now(), "actor": actor}),
        )
    emit({"content_hash": content_hash})


@command()
def new(
    slug: str,
    workflow: str | None = None,
    style: Annotated[list[str] | None, typer.Option()] = None,
    polish: Annotated[list[str] | None, typer.Option()] = None,
    style_intensity: str = "medium",
    scenario: str | None = None,
):
    """创建一个 run；作者资料须先确认。"""
    identifier(slug)
    root = project()
    config = profiles.profile(root)
    workflow = workflow or config["workflow"]
    scenario = scenario or config["style"].get("default_scenario", workflow)
    identifier(scenario)
    require(profiles.author_confirmed(root), "AUTHOR_CONFIRMATION_REQUIRED", "confirm-author")
    require(style_intensity in {"low", "medium", "high"}, "INVALID_INTENSITY", style_intensity)
    preset = profiles.scenario_preset(config, scenario)
    selection = (style or ([preset["scene"]] if preset.get("scene") else [])) + (
        polish or preset.get("polish", [])
    )
    for item in selection:
        styles.pack(item)
    flow = workflows.load(workflow)
    profiles.ensure_scenario(root, scenario)
    run_id = f"{date.today().isoformat()}-{slug}"
    path = safe_path(root, ".content-harness/runs/" + run_id)
    with lock(path):
        run = Run.create(path, run_id, flow, selection, style_intensity, scenario=scenario)
        emit({"run_id": run_id, "path": str(path), "revision": run.state.revision})


@command()
def status(run_id: str, json: bool = False):
    """扫描手工修改并显示资产和可执行任务。"""
    with session(run_id) as (run, _):
        emit(run.report())


@command()
def resume(run_id: str, json: bool = False):
    """从日志重建状态，只返回下一步，不重写文章。"""
    with session(run_id) as (run, _):
        emit(run.report())


@command()
def check(run_id: str, artifact: str | None = None, gate: str | None = None, json: bool = False):
    """校验并登记资产；失败保留文件并返回非零状态。"""
    require(not (artifact and gate), "INVALID_ARGUMENT", "choose artifact or gate")
    with session(run_id) as (run, _):
        if gate:
            require(gate in run.workflow["gates"], "GATE_UNKNOWN", gate)
            name = run.workflow["gates"][gate]
            require(
                run.state.artifacts[name].status == "done" and not run.blockers(name),
                "GATE_BLOCKED",
                gate,
            )
            validate_artifact(run, name)
            emit(
                {
                    "gate": gate,
                    "ready_for_approval": True,
                    "approved": run.approved(gate),
                    "revision": run.state.revision,
                }
            )
            return
        names = [artifact] if artifact else run.order
        errors = []
        for name in names:
            run.artifact_path(name)
            try:
                if run.state.artifacts[name].status != "done":
                    run.register(name)
                else:
                    validate_artifact(run, name)
            except (HarnessError, ValidationError, ValueError, OSError) as exc:
                errors.append({"artifact": name, "reason": str(exc)})
                record = run.state.artifacts[name]
                if record.status not in {"missing", "stale"}:
                    record.status, record.reason = "blocked", str(exc)
                    run.invalidate_descendants({name})
                    run.save("check-failed:" + name)
        if errors:
            raise HarnessError("CHECK_FAILED", json_module(errors))
        emit({"checked": names, "revision": run.state.revision})


def json_module(value):
    return json.dumps(value, ensure_ascii=False)


@command()
def put(
    run_id: str,
    artifact: str,
    source: Annotated[Path, typer.Option("--from")],
    expected_hash: Annotated[str, typer.Option()],
):
    """以 CAS 导入单个资产文件；初次写入使用 --expected-hash missing。"""
    data = source.read_bytes()
    with session(run_id) as (run, _):
        path = run.artifact_path(artifact)
        require(
            artifact not in {"publish-package", "style-spec"},
            "USE_SPECIAL_COMMAND",
            "package or style",
        )
        require(
            run.hash(artifact) == (None if expected_hash == "missing" else expected_hash),
            "CONFLICT_EXTERNAL_EDIT",
            artifact,
        )
        # Preserve exact observed bytes in a snapshot before an authorized replacement.
        if path.exists():
            run.snapshot(artifact)
        atomic_write(path, data)
        run.scan()
        emit(
            {
                "artifact": artifact,
                "content_hash": run.hash(artifact),
                "revision": run.state.revision,
                "next": "check --artifact " + artifact,
            }
        )


@command()
def approve(
    run_id: str,
    gate: str,
    chat_confirmed: bool = False,
    expected_hash: str | None = None,
    expected_revision: int | None = None,
    preview: bool = False,
):
    """用户交互确认，绑定当前资产哈希与 revision；不执行外部发布。"""
    with session(run_id) as (run, _):
        require(gate in run.workflow["gates"], "GATE_UNKNOWN", gate)
        name = run.workflow["gates"][gate]
        record = run.state.artifacts[name]
        require(record.status == "done" and not run.blockers(name), "GATE_BLOCKED", gate)
        validate_artifact(run, name)
        expected, revision = record.content_hash, record.revision
        if preview:
            emit({"gate": gate, "artifact": name, "content_hash": expected,
                  "artifact_revision": revision, "path": str(run.artifact_path(name))})
            return
        if chat_confirmed:
            require(expected_revision == revision, "CONFLICT_EXTERNAL_EDIT", name)
        actor = human_confirm(
            f"{gate}: {run.artifact_path(name)}", expected, chat_confirmed, expected_hash
        )
        run.scan()
        require(
            record.status == "done"
            and record.content_hash == expected
            and record.revision == revision,
            "CONFLICT_EXTERNAL_EDIT",
            name,
        )
        run.state.approvals.append(
            Approval(
                approval_id=uuid.uuid4().hex,
                at=now(),
                gate=gate,
                artifact=name,
                content_hash=expected,
                artifact_revision=revision,
                actor=actor,
            )
        )
        run.save("approve:" + gate)
        emit({"gate": gate, "content_hash": expected, "revision": run.state.revision})


@command()
def verify_claim(
    run_id: str, claim_id: str, chat_confirmed: bool = False, expected_hash: str | None = None,
    preview: bool = False,
):
    """用户核验高风险事实或确认亲历；绑定具体 claim 内容。"""
    with session(run_id) as (run, _):
        claim = next((c for c in ledger(run).claims if c.claim_id == claim_id), None)
        require(claim is not None, "CLAIM_UNKNOWN", claim_id)
        value = claim_hash(claim, run.hash("sources"))
        if preview:
            emit({"claim": claim.model_dump(), "content_hash": value})
            return
        human_confirm(claim.model_dump_json(indent=2), value, chat_confirmed, expected_hash)
        current = next((c for c in ledger(run).claims if c.claim_id == claim_id), None)
        require(
            current is not None and claim_hash(current, run.hash("sources")) == value,
            "CONFLICT_EXTERNAL_EDIT",
            claim_id,
        )
        run.state.claim_verifications[claim_id] = value
        run.save("verify-claim:" + claim_id + (":chat" if chat_confirmed else ""))
        emit({"claim_id": claim_id, "revision": run.state.revision})


@command()
def verify_claims(
    run_id: str, chat_confirmed: bool = False, expected_hash: str | None = None,
    preview: bool = False,
):
    """由用户一次核验当前全部待确认亲历与高风险事实。"""
    with session(run_id) as (run, _):
        items = claim_verification_items(run, pending_only=True)
        require(bool(items), "NO_CLAIMS_TO_VERIFY", run_id)
        value = claim_batch_hash(items)
        if preview:
            emit({"claims": items, "content_hash": value})
            return
        human_confirm(
            json.dumps({"claims": items}, ensure_ascii=False, indent=2),
            value,
            chat_confirmed,
            expected_hash,
        )
        current = claim_verification_items(run, pending_only=True)
        require(
            [item["claim_id"] for item in current] == [item["claim_id"] for item in items]
            and claim_batch_hash(current) == value,
            "CONFLICT_EXTERNAL_EDIT",
            "claims",
        )
        run.state.claim_verifications.update(
            {item["claim_id"]: item["content_hash"] for item in current}
        )
        run.save("verify-claims:chat" if chat_confirmed else "verify-claims")
        emit(
            {
                "claim_ids": [item["claim_id"] for item in current],
                "content_hash": value,
                "revision": run.state.revision,
            }
        )


@command()
def invalidate(run_id: str, artifact: str, reason: Annotated[str, typer.Option()]):
    """将目标及下游设为 stale，保留所有文件。"""
    with session(run_id) as (run, _):
        run.artifact_path(artifact)
        record = run.state.artifacts[artifact]
        record.status, record.reason = "stale", reason
        record.revision += 1
        affected = run.invalidate_descendants({artifact})
        run.save("invalidate:" + artifact)
        emit({"affected": sorted(affected), "revision": run.state.revision})


@command()
def voice(
    run_id: str,
    use: Annotated[list[str] | None, typer.Option()] = None,
    intensity: str | None = None,
    reset: bool = False,
):
    """编译作者、场景与正反样稿约束，供 Brief 及后续写作使用。"""
    require(not (reset and use), "INVALID_ARGUMENT", "reset or use")
    with session(run_id) as (run, root):
        selection = [] if reset else (use if use is not None else run.state.style_selection)
        selected_intensity = intensity or run.state.style_intensity
        require(
            selected_intensity in {"low", "medium", "high"},
            "INVALID_INTENSITY",
            selected_intensity,
        )
        config = profiles.profile(root)
        require(
            config["style"].get("allow_run_override", True)
            or (selection == run.state.style_selection and selected_intensity == run.state.style_intensity),
            "STYLE_OVERRIDE_DISABLED",
            "project profile",
        )
        selection = list(dict.fromkeys(selection))
        for style_id in selection:
            styles.pack(style_id)
        if selection != run.state.style_selection or selected_intensity != run.state.style_intensity:
            run.state.style_selection = selection
            run.state.style_intensity = selected_intensity
            run.save("voice-selection")
        result = styles.compile_voice_contract(run, root)
        emit({"voice_contract": result, "revision": run.state.revision})


@command()
def style(
    run_id: str,
    use: Annotated[list[str] | None, typer.Option()] = None,
    intensity: str | None = None,
    reset: bool = False,
):
    """编译并固化风格；--reset 关闭额外风格。"""
    require(not (reset and use), "INVALID_ARGUMENT", "reset or use")
    with session(run_id) as (run, root):
        selection = [] if reset else (use if use is not None else run.state.style_selection)
        result = styles.compile_style(run, root, selection, intensity or run.state.style_intensity)
        emit({"style_spec": result, "revision": run.state.revision})


@command()
def style_feedback(
    run_id: str,
    reason: Annotated[str, typer.Option()],
    artifact: str = "manuscript",
    scope: str = "run",
    before_hash: str | None = None,
):
    """保存已登记版本与当前手改稿的差异，支持发布稿和历史基线。"""
    with session(run_id) as (run, root):
        emit(
            {
                "lesson": styles.feedback(run, root, artifact, scope, reason, before_hash=before_hash),
                "revision": run.state.revision,
            }
        )


@command()
def style_note(
    run_id: str,
    reason: Annotated[str, typer.Option()],
    artifact: str = "manuscript",
    scope: str = "run",
    reference_path: str | None = None,
    reference_excerpt: str | None = None,
):
    """记录拒稿或对标反馈，无需先由用户手工改稿。"""
    with session(run_id) as (run, root):
        emit(
            {
                "lesson": styles.note_feedback(
                    run,
                    root,
                    artifact,
                    scope,
                    reason,
                    reference_path=reference_path,
                    reference_excerpt=reference_excerpt,
                ),
                "revision": run.state.revision,
            }
        )


@command()
def style_promote(
    run_id: str, lesson_id: str, chat_confirmed: bool = False, expected_hash: str | None = None,
    preview: bool = False,
):
    """用户确认候选后，写入作者或场景记忆。"""
    root = project()
    identifier(run_id)
    identifier(lesson_id)
    path = safe_path(root, f".content-harness/style-memory/candidates/{lesson_id}.yaml")
    data = path.read_bytes()
    Feedback.model_validate(read_yaml(path))
    if preview:
        emit({"candidate": read_yaml(path), "content_hash": digest(data)})
        return
    actor = human_confirm(data.decode(), digest(data), chat_confirmed, expected_hash)
    emit({"memory": styles.promote(root, run_id, lesson_id, digest(data), actor=actor)})


@command()
def style_rollback(
    scope: str,
    version: int,
    scenario: str | None = None,
    chat_confirmed: bool = False,
    expected_hash: str | None = None,
    expected_version_hash: str | None = None,
    preview: bool = False,
):
    """用户将指定旧版本恢复为新版本，保留历史。"""
    root = project()
    config = profiles.profile(root)
    scenario = scenario or config["style"].get("default_scenario", config["workflow"])
    memory_root = safe_path(root, ".content-harness/style-memory")
    path = styles.memory_target(memory_root, scope, scenario)
    expected = digest(path.read_bytes())
    old = styles.version_path(memory_root, path, version)
    if not old.exists() and scope == "scenario" and scenario != "author":
        old = safe_path(memory_root, f"versions/{path.stem}/{version}.yaml")
    old_hash = digest(old.read_bytes())
    if preview:
        emit({"current": read_yaml(path), "target": read_yaml(old),
              "content_hash": expected, "version_hash": old_hash})
        return
    actor = human_confirm(
        f"恢复为版本 {version}\n{old.read_text()}", expected, chat_confirmed, expected_hash
    )
    if chat_confirmed:
        require(expected_version_hash == old_hash, "CONFLICT_EXTERNAL_EDIT", "历史版本已变化")
    emit(
        {
            "memory": styles.rollback(
                root, scope, scenario, version, expected,
                actor=actor, expected_version_hash=old_hash,
            )
        }
    )


@command()
def package(
    run_id: str,
    titles: Annotated[Path, typer.Option()],
    summary: Annotated[Path, typer.Option()],
    expected_hash: str = "missing",
):
    """从已评审正文和图片构建公众号发布包。"""
    with session(run_id) as (run, _):
        exporting.package(run, titles, summary, expected_hash)
        emit({"path": str(run.artifact_path("publish-package")), "revision": run.state.revision})


@command()
def export(run_id: str, target: str | None = None):
    """审批后导出到配置目录，已有文件冲突时拒绝覆盖。"""
    with session(run_id) as (run, root):
        emit({**exporting.export(run, root, target), "revision": run.state.revision})


@command()
def archive(run_id: str):
    """归档 run，文件可恢复，无物理删除。"""
    with session(run_id) as (run, root):
        destination = safe_path(root, ".content-harness/archive/" + run_id)
        require(not destination.exists(), "ARCHIVE_CONFLICT", str(destination))
        destination.parent.mkdir(parents=True, exist_ok=True)
        run.state.archived = True
        run.save("archive")
        run.path.rename(destination)
        emit({"path": str(destination), "revision": run.state.revision})


@command()
def restore(run_id: str):
    """恢复已归档 run，保留完整事件历史。"""
    identifier(run_id)
    root = project()
    archived = safe_path(root, ".content-harness/archive/" + run_id)
    destination = safe_path(root, ".content-harness/runs/" + run_id)
    source = archived if archived.exists() else destination
    require(source.exists(), "RUN_NOT_FOUND", run_id)
    with lock(source):
        run = Run(source)
        require(run.state.archived, "RUN_NOT_ARCHIVED", run_id)
        if source != destination:
            require(not destination.exists(), "RESTORE_CONFLICT", str(destination))
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            run.path = destination
        run.state.archived = False
        run.save("restore")
        run.scan()
        emit({"path": str(destination), "revision": run.state.revision})


@command()
def check_workflow(workflow_id: Annotated[str, typer.Argument()] = "wechat-longform"):
    """校验 DAG、Skill 和 gate 引用。"""
    flow = workflows.load(workflow_id)
    emit({"workflow": workflow_id, "order": workflows.validate(flow)})


@command()
def install_skills(client: str = "codex", destination: Path | None = None):
    """安装独立 Skills，默认项目级目录；存在不同内容时拒绝覆盖。"""
    paths = {"codex": ".agents/skills", "claude": ".claude/skills", "cursor": ".cursor/skills"}
    require(client in paths, "CLIENT_UNKNOWN", client)
    target = (
        destination.resolve() if destination else safe_path(project_option.resolve(), paths[client])
    )
    source = workflows.resources() / "skills"
    installed = []
    # Preflight all conflicts before installing any skill.
    for entry in sorted(source.iterdir()):
        dest = safe_path(target, entry.name)
        if dest.exists():
            require(tree_hash(files(dest)) == tree_hash(files(entry)), "SKILL_CONFLICT", str(dest))
    for entry in sorted(source.iterdir()):
        dest = safe_path(target, entry.name)
        if not dest.exists():
            shutil.copytree(entry, dest)
        installed.append(str(dest))
    emit(
        {
            "client": client,
            "installed": installed,
            "note": "Restart/reload the client to discover skills; behavior compatibility needs real-client verification",
        }
    )


@command()
def doctor():
    """检查版本、项目配置、作者确认和本地 Skill 发现位置。"""
    checks = {
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "workflow": workflows.load("wechat-longform")["id"],
    }
    try:
        root = project()
    except HarnessError:
        checks["project"] = "not_initialized"
        emit(checks)
        return
    checks.update(
        {
            "project": str(root),
            "profile": profiles.profile(root),
            "author_confirmed": profiles.author_confirmed(root),
            "writable": os.access(root / ".content-harness", os.W_OK),
            "local_skills": {
                client: (root / relative / "content-harness/SKILL.md").exists()
                for client, relative in {
                    "codex": ".agents/skills",
                    "claude": ".claude/skills",
                    "cursor": ".cursor/skills",
                }.items()
            },
        }
    )
    emit(checks)


def main():
    app()


if __name__ == "__main__":
    main()
