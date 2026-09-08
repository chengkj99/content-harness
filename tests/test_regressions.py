import pytest
from conftest import build_to_brief, build_to_manuscript

from content_harness import styles
from content_harness.gates import claim_hash, ledger, validate_artifact
from content_harness.storage import HarnessError, atomic_write, read_yaml, yaml_bytes


def test_source_edit_revokes_high_risk_verification(workspace):
    _, run = workspace
    build_to_brief(run)
    claims = read_yaml(run.artifact_path("claims"))
    claims["claims"][0]["risk"] = "high"
    atomic_write(run.artifact_path("claims"), yaml_bytes(claims))
    run.scan()
    claim = ledger(run).claims[0]
    run.state.claim_verifications[claim.claim_id] = claim_hash(claim, run.hash("sources"))
    run.register("claims")
    source = read_yaml(run.artifact_path("sources"))
    source["sources"][0]["excerpt"] = "changed evidence"
    atomic_write(run.artifact_path("sources"), yaml_bytes(source))
    run.scan()
    run.register("sources")
    with pytest.raises(HarnessError) as error:
        run.register("claims")
    assert error.value.code == "CLAIM_HUMAN_REQUIRED"


@pytest.mark.parametrize(
    "content",
    [
        "![image](https://example.com/x.png)",
        '<img src="https://example.com/x.png">',
        "[link][ref]\n\n[ref]: missing.md",
    ],
)
def test_untracked_link_syntax_refused(workspace, content):
    _, run = workspace
    atomic_write(run.artifact_path("idea"), content.encode())
    with pytest.raises(HarnessError):
        validate_artifact(run, "idea")


def test_style_compiler_never_overwrites_manual_spec(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    path = run.artifact_path("style-spec")
    edited = path.read_bytes() + b"\n# User edit"
    atomic_write(path, edited)
    run.scan()
    with pytest.raises(HarnessError) as error:
        styles.compile_style(run, project, [], "low")
    assert error.value.code == "CONFLICT_EXTERNAL_EDIT"
    assert path.read_bytes() == edited
