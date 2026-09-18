import pytest
from conftest import (
    approve_fixture,
    build_package,
    build_reviews,
    build_to_brief,
    build_to_manuscript,
)

from content_harness import exporting
from content_harness.gates import claim_hash, ledger, validate_artifact
from content_harness.storage import HarnessError, atomic_write, read_yaml, safe_path, yaml_bytes


@pytest.mark.parametrize(
    "before,after",
    [("2 次", "20 次"), ("可能", "保证"), ("当前样本", "所有用户"), ("claim:c1", "claim:c2")],
)
def test_style_drift_blocked(workspace, before, after):
    project, run = workspace
    build_to_manuscript(run, project)
    path = run.artifact_path("manuscript")
    atomic_write(path, path.read_text().replace(before, after).encode())
    run.scan()
    with pytest.raises(HarnessError):
        run.register("manuscript")


def test_style_report_requires_evidence_for_every_selected_style(workspace):
    project, run = workspace
    build_to_manuscript(run, project, ["natural-human-zh"])
    data = {
        "input_hashes": {
            dep: run.state.artifacts[dep].content_hash
            for dep in run.workflow["artifacts"]["style-report"]["depends_on"]
        },
        "changes": [],
        "rejected": [],
        "fidelity": "pass",
        "reason": "No-op without evidence",
        "rule_assessments": [],
    }
    atomic_write(run.artifact_path("style-report"), yaml_bytes(data))
    run.scan()
    with pytest.raises(HarnessError) as error:
        run.register("style-report")
    assert error.value.code == "STYLE_RULE_COVERAGE"


def test_style_report_rejects_duplicate_assessments(workspace):
    project, run = workspace
    build_to_manuscript(run, project, ["natural-human-zh"])
    assessment = {
        "style_id": "natural-human-zh",
        "status": "already-satisfied",
        "evidence": "Synthetic fixture body",
    }
    data = {
        "input_hashes": {
            dep: run.state.artifacts[dep].content_hash
            for dep in run.workflow["artifacts"]["style-report"]["depends_on"]
        },
        "changes": [],
        "rejected": [],
        "fidelity": "pass",
        "reason": "Duplicated coverage",
        "rule_assessments": [assessment, assessment],
    }
    atomic_write(run.artifact_path("style-report"), yaml_bytes(data))
    run.scan()
    with pytest.raises(HarnessError) as error:
        run.register("style-report")
    assert error.value.code == "STYLE_RULE_COVERAGE"


def test_personal_narrative_voice_review_requires_signature(workspace):
    project, run = workspace
    build_to_manuscript(run, project, ["personal-narrative-zh"])
    build_reviews(run)
    data = read_yaml(run.artifact_path("voice-review"))
    data["signature_passage"] = None
    atomic_write(run.artifact_path("voice-review"), yaml_bytes(data))
    run.scan()
    with pytest.raises(HarnessError) as error:
        run.register("voice-review")
    assert error.value.code == "VOICE_SIGNATURE_MISSING"


def test_unsupported_factual_claim_blocks(workspace):
    _, run = workspace
    build_to_brief(run)
    value = read_yaml(run.artifact_path("claims"))
    value["claims"][0].update(type="factual", status="supported", sources=[])
    atomic_write(run.artifact_path("claims"), yaml_bytes(value))
    run.scan()
    with pytest.raises(HarnessError) as error:
        run.register("claims")
    assert error.value.code == "CLAIM_UNSUPPORTED"


def test_high_risk_verification_bound_to_claim_hash(workspace):
    _, run = workspace
    build_to_brief(run)
    value = read_yaml(run.artifact_path("claims"))
    value["claims"][0]["risk"] = "high"
    atomic_write(run.artifact_path("claims"), yaml_bytes(value))
    run.scan()
    with pytest.raises(HarnessError) as error:
        run.register("claims")
    assert error.value.code == "CLAIM_HUMAN_REQUIRED"
    claim = ledger(run).claims[0]
    run.state.claim_verifications[claim.claim_id] = claim_hash(claim, run.hash("sources"))
    run.register("claims")
    value["claims"][0]["text"] = "Changed claim"
    atomic_write(run.artifact_path("claims"), yaml_bytes(value))
    run.scan()
    with pytest.raises(HarnessError):
        run.register("claims")


@pytest.mark.parametrize(
    "target", ["../outside", "/tmp/outside", ".git/hooks/evil", ".content-harness/overwrite"]
)
def test_export_path_boundary(workspace, target):
    project, run = workspace
    build_package(run, project)
    approve_fixture(run, "publish")
    path = project / ".content-harness/project.yaml"
    data = read_yaml(path)
    data["exports"]["wechat"]["directory"] = target
    atomic_write(path, yaml_bytes(data))
    with pytest.raises(HarnessError):
        exporting.export(run, project, "wechat")


def test_existing_export_never_overwritten(workspace):
    project, run = workspace
    build_package(run, project)
    approve_fixture(run, "publish")
    destination = project / "content" / run.state.run_id
    destination.mkdir(parents=True)
    atomic_write(destination / "article.md", b"user content")
    with pytest.raises(HarnessError) as error:
        exporting.export(run, project, "wechat")
    assert error.value.code == "EXPORT_CONFLICT"
    assert (destination / "article.md").read_bytes() == b"user content"


def test_symlink_refused(workspace, tmp_path):
    project, _ = workspace
    (project / "escape").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(HarnessError):
        safe_path(project, "escape/file")


@pytest.mark.parametrize(
    "content",
    [
        "[missing](missing.md)",
        "[bad](javascript:alert)",
        "![outside](../outside.png)",
        "[encoded](%2e%2e/outside.md)",
    ],
)
def test_bad_links_blocked(workspace, content):
    _, run = workspace
    atomic_write(run.artifact_path("idea"), content.encode())
    with pytest.raises(HarnessError):
        validate_artifact(run, "idea")


def test_secret_gate(workspace):
    _, run = workspace
    atomic_write(run.artifact_path("idea"), ("token: ghp_" + "x" * 30).encode())
    with pytest.raises(HarnessError) as error:
        validate_artifact(run, "idea")
    assert error.value.code == "SECRET_DETECTED"


def test_package_cannot_change_reviewed_article(workspace):
    project, run = workspace
    build_package(run, project)
    atomic_write(run.artifact_path("publish-package") / "article.md", b"New unsupported promise")
    run.scan()
    with pytest.raises(HarnessError) as error:
        run.register("publish-package")
    assert error.value.code == "PACKAGE_CONTENT_CHANGED"


def test_image_bytes_invalidate_package(workspace):
    project, run = workspace
    build_package(run, project)
    # Even an unlisted new image changes the visual-assets aggregate hash.
    atomic_write(
        run.path / "artifacts/assets/new.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    )
    run.scan()
    assert run.state.artifacts["visual-assets"].status == "in_progress"
    assert run.state.artifacts["publish-package"].status == "stale"
