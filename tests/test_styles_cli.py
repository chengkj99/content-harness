import json

import pytest
from conftest import approve_fixture, build_package, build_to_brief, build_to_manuscript
from typer.testing import CliRunner

from content_harness import profiles, styles
from content_harness.cli import app
from content_harness.gates import claim_batch_hash, claim_verification_items, ledger
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


def test_style_switch_after_voice_contract_leaves_completed_run_unchanged(workspace):
    project, run = workspace
    build_package(run, project)
    with pytest.raises(HarnessError) as error:
        styles.compile_style(run, project, ["natural-human-zh"], "medium")
    assert error.value.code == "VOICE_STYLE_MISMATCH"
    assert run.state.artifacts["brief"].status == "done"
    assert run.state.artifacts["claims"].status == "done"
    assert run.state.artifacts["outline"].status == "done"
    assert run.state.artifacts["publish-package"].status == "done"


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


def test_style_note_records_rejection_without_manual_diff(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    lesson = styles.note_feedback(
        run,
        project,
        "manuscript",
        "scenario",
        "作者退场，文章变成通用方法文",
        reference_excerpt="先从真实谈话进入，再回到作者经历",
    )
    assert lesson["evidence_type"] == "reference-comparison"
    assert lesson["diff"] == ""
    assert lesson["before_hash"] == lesson["after_hash"]
    candidate = (
        project / ".content-harness/style-memory/candidates" / (lesson["lesson_id"] + ".yaml")
    )
    assert candidate.is_file()


def test_reference_change_stales_voice_contract_and_downstream(workspace):
    project, run = workspace
    reference = project / "voice-reference.yaml"
    atomic_write(
        reference,
        yaml_bytes(
            {
                "references": [
                    {
                        "reference_id": "positive-1",
                        "role": "positive",
                        "source": "Synthetic approved sample",
                        "dimensions": ["作者特异性"],
                        "excerpt": "只有这个作者能说出的具体经历。",
                        "reason": "用真实经历承担判断。",
                    }
                ]
            }
        ),
    )
    profiles.configure(project, reference_files=["voice-reference.yaml"])
    build_to_brief(run)
    contract = read_yaml(run.artifact_path("voice-contract"))
    assert contract["references"][0]["reference_id"] == "positive-1"
    atomic_write(reference, reference.read_bytes() + b"\n")
    assert styles.scan_voice_contract(run, project)
    assert run.state.artifacts["voice-contract"].status == "stale"
    assert run.state.artifacts["brief"].status == "stale"


def test_voice_contract_embeds_style_rules_and_memory_evals(workspace):
    project, run = workspace
    run.state.style_selection = ["personal-narrative-zh", "natural-human-zh"]
    run.save("test-style-selection")
    memory = project / ".content-harness/style-memory/author.yaml"
    atomic_write(
        memory,
        yaml_bytes(
            {
                "version": 1,
                "rules": [
                    {
                        "lesson_id": "lesson-voice",
                        "rule": "作者持续在场",
                        "eval": "正文中段仍有作者经历与判断",
                    }
                ],
            }
        ),
    )
    build_to_brief(run)
    contract = read_yaml(run.artifact_path("voice-contract"))
    assert [item["id"] for item in contract["style_packs"]] == [
        "personal-narrative-zh",
        "natural-human-zh",
    ]
    assert contract["selected_styles"] == ["personal-narrative-zh", "natural-human-zh"]
    assert "author-memory:lesson-voice" in contract["required_dimensions"]
    assert contract["dimension_guidance"]["author-memory:lesson-voice"] == (
        "正文中段仍有作者经历与判断"
    )


def test_style_cannot_change_after_voice_contract_and_brief_approval(workspace):
    project, run = workspace
    build_to_brief(run)
    approve_fixture(run, "brief")
    with pytest.raises(HarnessError) as error:
        styles.compile_style(run, project, ["natural-human-zh"], "medium")
    assert error.value.code == "VOICE_STYLE_MISMATCH"


def test_voice_command_changes_style_and_stales_existing_brief(workspace):
    project, run = workspace
    build_to_brief(run)
    result = call(
        project,
        "voice",
        run.state.run_id,
        "--use",
        "personal-narrative-zh",
        "--intensity",
        "high",
    )
    assert result.exit_code == 0, result.output
    refreshed = Run(run.path)
    contract = read_yaml(refreshed.artifact_path("voice-contract"))
    assert contract["selected_styles"] == ["personal-narrative-zh"]
    assert contract["style_intensity"] == "high"
    assert refreshed.state.artifacts["brief"].status == "stale"


@pytest.mark.parametrize(
    "command", ["approve", "verify-claim", "verify-claims", "confirm-author"]
)
def test_non_tty_human_operations_refused(workspace, command):
    project, run = workspace
    build_to_brief(run)
    if command == "verify-claims":
        value = read_yaml(run.artifact_path("claims"))
        value["claims"][0].update(
            type="experience",
            status="author-confirmed",
            provenance="Synthetic author statement",
        )
        atomic_write(run.artifact_path("claims"), yaml_bytes(value))
        run.scan()
    args = {
        "approve": [run.state.run_id, "brief"],
        "verify-claim": [run.state.run_id, "c1"],
        "verify-claims": [run.state.run_id],
        "confirm-author": [],
    }
    result = call(project, command, *args[command])
    assert result.exit_code == 1, result.output
    assert "HUMAN_TTY_REQUIRED" in result.output


def test_tty_batch_claim_verification_roundtrip(workspace, monkeypatch):
    project, run = workspace
    build_to_brief(run)
    claim = ledger(run).claims[0]
    claim.type = "experience"
    claim.status = "author-confirmed"
    claim.provenance = "Synthetic author statement"
    atomic_write(run.artifact_path("claims"), yaml_bytes({"claims": [claim.model_dump()]}))
    run.scan()
    monkeypatch.setattr("content_harness.cli.is_tty", lambda: True)
    items = claim_verification_items(run, pending_only=True)
    expected = claim_batch_hash(items)
    monkeypatch.setattr("content_harness.cli.typer.prompt", lambda _: expected)
    result = call(project, "verify-claims", run.state.run_id)
    assert result.exit_code == 0, result.output
    refreshed = Run(run.path)
    assert refreshed.state.claim_verifications[claim.claim_id] == items[0]["content_hash"]


def test_tty_approval_roundtrip_and_input_change(workspace, monkeypatch):
    project, run = workspace
    build_to_brief(run)
    monkeypatch.setattr("content_harness.cli.is_tty", lambda: True)
    expected = run.state.artifacts["brief"].content_hash
    monkeypatch.setattr("content_harness.cli.typer.prompt", lambda _: expected)
    result = call(project, "approve", run.state.run_id, "brief")
    assert result.exit_code == 0, result.output
    assert Run(run.path).approved("brief")


def test_chat_approval_requires_observed_hash_and_artifact_revision(workspace):
    project, run = workspace
    build_to_brief(run)
    record = run.state.artifacts["brief"]
    args = [
        run.state.run_id, "brief", "--chat-confirmed", "--expected-hash", record.content_hash,
        "--expected-revision", str(record.revision),
    ]
    assert "CONFLICT_EXTERNAL_EDIT" in call(project, "approve", *args[:-2]).output
    assert "CONFLICT_EXTERNAL_EDIT" in call(
        project, "approve", *args[:-1], str(record.revision + 1)
    ).output
    assert not Run(run.path).approved("brief")
    result = call(project, "approve", *args)
    assert result.exit_code == 0, result.output
    refreshed = Run(run.path)
    assert refreshed.approved("brief")
    assert refreshed.state.approvals[-1].actor == "human:agent-chat"


def test_chat_approval_rejects_changed_content_even_after_revert(workspace):
    project, run = workspace
    build_to_brief(run)
    record = run.state.artifacts["brief"]
    old_hash, old_revision = record.content_hash, record.revision
    original = run.artifact_path("brief").read_bytes()
    atomic_write(run.artifact_path("brief"), original + b"\nchanged")
    call(project, "status", run.state.run_id)
    atomic_write(run.artifact_path("brief"), original)
    assert call(project, "check", run.state.run_id, "--artifact", "brief").exit_code == 0
    result = call(
        project, "approve", run.state.run_id, "brief", "--chat-confirmed",
        "--expected-hash", old_hash, "--expected-revision", str(old_revision),
    )
    assert "CONFLICT_EXTERNAL_EDIT" in result.output
    assert not Run(run.path).approved("brief")


def test_chat_confirm_author_requires_current_hash(workspace):
    project, _ = workspace
    current = profiles.author_hash(project)
    bad = call(project, "confirm-author", "--chat-confirmed", "--expected-hash", "sha256:old")
    assert "CONFLICT_EXTERNAL_EDIT" in bad.output
    result = call(project, "confirm-author", "--chat-confirmed", "--expected-hash", current)
    assert result.exit_code == 0, result.output
    confirmation = read_yaml(project / ".content-harness/author-confirmation.yaml")
    assert confirmation["actor"] == "human:agent-chat"


def test_chat_verify_claims_rejects_changed_batch(workspace):
    project, run = workspace
    build_to_brief(run)
    claim = ledger(run).claims[0]
    claim.type = "experience"
    claim.status = "author-confirmed"
    claim.provenance = "Synthetic author statement"
    atomic_write(run.artifact_path("claims"), yaml_bytes({"claims": [claim.model_dump()]}))
    run.scan()
    expected = claim_batch_hash(claim_verification_items(run, pending_only=True))
    claim.text = "Changed claim"
    atomic_write(run.artifact_path("claims"), yaml_bytes({"claims": [claim.model_dump()]}))
    result = call(
        project, "verify-claims", run.state.run_id, "--chat-confirmed", "--expected-hash", expected
    )
    assert "CONFLICT_EXTERNAL_EDIT" in result.output
    assert not Run(run.path).state.claim_verifications


def test_chat_style_promotion_and_rollback_require_reviewed_versions(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    lesson = styles.note_feedback(run, project, "manuscript", "scenario", "结尾更具体")
    lesson.update(proposed_rule="结尾给出动作", eval_proposal="检查结尾是否有动作")
    candidate = (
        project / ".content-harness/style-memory/candidates" / (lesson["lesson_id"] + ".yaml")
    )
    atomic_write(candidate, yaml_bytes(lesson))
    preview = call(project, "style-promote", run.state.run_id, lesson["lesson_id"], "--preview")
    assert preview.exit_code == 0, preview.output
    candidate_hash = json.loads(preview.output)["content_hash"]
    bad = call(
        project, "style-promote", run.state.run_id, lesson["lesson_id"],
        "--chat-confirmed", "--expected-hash", "sha256:old",
    )
    assert "CONFLICT_EXTERNAL_EDIT" in bad.output
    good = call(
        project, "style-promote", run.state.run_id, lesson["lesson_id"],
        "--chat-confirmed", "--expected-hash", candidate_hash,
    )
    assert good.exit_code == 0, good.output
    memory = project / ".content-harness/style-memory/scenarios/wechat-longform.yaml"
    assert read_yaml(memory)["rules"][-1]["actor"] == "human:agent-chat"
    preview = call(project, "style-rollback", "scenario", "0", "--preview")
    assert preview.exit_code == 0, preview.output
    observed = json.loads(preview.output)
    args = [
        "scenario", "0", "--chat-confirmed", "--expected-hash", observed["content_hash"],
        "--expected-version-hash", observed["version_hash"],
    ]
    assert "CONFLICT_EXTERNAL_EDIT" in call(project, "style-rollback", *args[:-2]).output
    result = call(project, "style-rollback", *args)
    assert result.exit_code == 0, result.output
    assert read_yaml(memory)["actor"] == "human:agent-chat"


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
