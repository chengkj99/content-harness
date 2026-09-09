import json

import pytest
from conftest import approve_fixture, build_package, build_to_brief, build_to_manuscript
from typer.testing import CliRunner

from content_harness import profiles, styles
from content_harness.cli import app
from content_harness.state import Run
from content_harness.storage import HarnessError, atomic_write, digest, read_yaml, yaml_bytes

runner = CliRunner()


def call(project, *args, **kwargs):
    return runner.invoke(app, ["--project", str(project), *args], **kwargs)


@pytest.mark.parametrize(
    "selection",
    [
        [],
        ["wechat-high-engagement"],
        ["natural-human-zh"],
        ["wechat-high-engagement", "natural-human-zh"],
    ],
)
def test_style_optional_and_composable(workspace, selection):
    project, run = workspace
    build_to_manuscript(run, project, selection)
    spec = read_yaml(run.artifact_path("style-spec"))
    stack = spec["style_stack"]
    assert [p["id"] for p in stack["scene"] + stack["polish"]] == selection
    assert spec["base"]["id"] == "neutral"


def test_memory_snapshot_is_not_live_dependency(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    before = run.artifact_path("style-spec").read_bytes()
    atomic_write(
        project / ".content-harness/style-memory/author.yaml",
        yaml_bytes({"version": 1, "rules": ["New preference"]}),
    )
    run.scan()
    assert run.state.artifacts["style-spec"].status == "done"
    assert run.artifact_path("style-spec").read_bytes() == before


def test_style_switch_stales_only_downstream(workspace):
    project, run = workspace
    build_package(run, project)
    styles.compile_style(run, project, ["natural-human-zh"], "medium")
    assert run.state.artifacts["brief"].status == "done"
    assert run.state.artifacts["claims"].status == "done"
    assert run.state.artifacts["outline"].status == "stale"
    assert run.state.artifacts["publish-package"].status == "stale"


def test_feedback_promotion_and_rollback_scoped(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    path = run.artifact_path("manuscript")
    atomic_write(path, path.read_bytes() + "\n给一个明确的下一步。".encode())
    run.scan()
    lesson = styles.feedback(run, project, "manuscript", "scenario", "结尾更具体")
    root = project / ".content-harness/style-memory"
    candidate = root / "candidates" / (lesson["lesson_id"] + ".yaml")
    assert "下一步" in lesson["diff"]
    assert read_yaml(root / "scenarios/wechat-longform.yaml")["version"] == 0
    lesson.update(proposed_rule="结尾给出明确动作", eval_proposal="保留具体命令；删除空泛号召")
    atomic_write(candidate, yaml_bytes(lesson))
    result = styles.promote(
        project, run.state.run_id, lesson["lesson_id"], digest(candidate.read_bytes())
    )
    assert result["version"] == 1
    assert not (root / "scenarios/technical-tutorial.yaml").exists()
    assert read_yaml(root / "author.yaml")["version"] == 0
    current = root / "scenarios/wechat-longform.yaml"
    restored = styles.rollback(
        project, "scenario", "wechat-longform", 0, digest(current.read_bytes())
    )
    assert restored["version"] == 2 and restored["rules"] == []


def test_run_only_feedback_not_promoted(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    path = run.artifact_path("manuscript")
    atomic_write(path, path.read_bytes() + b"\nedit")
    run.scan()
    lesson = styles.feedback(run, project, "manuscript", "run", "one-off")
    lesson.update(proposed_rule="one-off", eval_proposal="compare")
    candidate = (
        project / ".content-harness/style-memory/candidates" / (lesson["lesson_id"] + ".yaml")
    )
    atomic_write(candidate, yaml_bytes(lesson))
    with pytest.raises(HarnessError):
        styles.promote(
            project, run.state.run_id, lesson["lesson_id"], digest(candidate.read_bytes())
        )


@pytest.mark.parametrize("command", ["approve", "verify-claim", "confirm-author"])
def test_non_tty_human_operations_refused(workspace, command):
    project, run = workspace
    build_to_brief(run)
    args = {
        "approve": [run.state.run_id, "brief"],
        "verify-claim": [run.state.run_id, "c1"],
        "confirm-author": [],
    }
    result = call(project, command, *args[command])
    assert result.exit_code == 1, result.output
    assert "HUMAN_TTY_REQUIRED" in result.output


def test_tty_approval_roundtrip_and_input_change(workspace, monkeypatch):
    project, run = workspace
    build_to_brief(run)
    monkeypatch.setattr("content_harness.cli.is_tty", lambda: True)
    expected = run.state.artifacts["brief"].content_hash
    monkeypatch.setattr("content_harness.cli.typer.prompt", lambda _: expected)
    result = call(project, "approve", run.state.run_id, "brief")
    assert result.exit_code == 0, result.output
    assert Run(run.path).approved("brief")


def test_cas_put_rejects_external_edit(workspace):
    project, run = workspace
    source = project / "source.md"
    atomic_write(source, b"new")
    atomic_write(run.artifact_path("idea"), b"human edit")
    result = call(
        project,
        "put",
        run.state.run_id,
        "idea",
        "--from",
        str(source),
        "--expected-hash",
        "missing",
    )
    assert result.exit_code == 1
    assert "CONFLICT_EXTERNAL_EDIT" in result.output
    assert run.artifact_path("idea").read_bytes() == b"human edit"


def test_put_and_status_json(workspace):
    project, run = workspace
    source = project / "source.md"
    atomic_write(source, b"new")
    result = call(
        project,
        "put",
        run.state.run_id,
        "idea",
        "--from",
        str(source),
        "--expected-hash",
        "missing",
    )
    assert result.exit_code == 0, result.output
    assert call(project, "check", run.state.run_id, "--artifact", "idea").exit_code == 0
    result = call(project, "status", run.state.run_id, "--json")
    data = json.loads(result.output)
    assert data["schema_version"] == 1 and data["ok"]
    assert data["ready"][0]["artifact"] == "sources"


def test_init_no_overwrite_and_author_gate(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert runner.invoke(app, ["init", str(tmp_path)]).exit_code == 1
    result = call(tmp_path, "new", "test")
    assert "AUTHOR_CONFIRMATION_REQUIRED" in result.output


@pytest.mark.parametrize("client", ["codex", "claude", "cursor"])
def test_skills_install_and_collision(tmp_path, client):
    destination = tmp_path / client
    result = runner.invoke(
        app, ["install-skills", "--client", client, "--destination", str(destination)]
    )
    assert result.exit_code == 0, result.output
    assert len(list(destination.glob("*/SKILL.md"))) == 13
    assert (
        runner.invoke(
            app, ["install-skills", "--client", client, "--destination", str(destination)]
        ).exit_code
        == 0
    )
    atomic_write(destination / "content-harness/SKILL.md", b"user skill")
    result = runner.invoke(
        app, ["install-skills", "--client", client, "--destination", str(destination)]
    )
    assert result.exit_code == 1
    assert "SKILL_CONFLICT" in result.output


def test_archive_preserves_files(workspace):
    project, run = workspace
    result = call(project, "archive", run.state.run_id)
    assert result.exit_code == 0, result.output
    archived = project / ".content-harness/archive" / run.state.run_id
    assert (archived / "transitions.jsonl").exists()
    assert not run.path.exists()
    result = call(project, "restore", run.state.run_id)
    assert result.exit_code == 0, result.output
    assert not Run(run.path).state.archived


def test_style_requires_brief_approval(workspace):
    project, run = workspace
    build_to_brief(run)
    result = call(project, "style", run.state.run_id)
    assert "APPROVAL_REQUIRED" in result.output
    approve_fixture(run, "brief")
    result = call(project, "style", run.state.run_id)
    assert result.exit_code == 0, result.output


def test_author_edit_revokes_confirmation(workspace):
    project, _ = workspace
    atomic_write(project / ".content-harness/author-profile.md", b"changed")
    assert not profiles.author_confirmed(project)
