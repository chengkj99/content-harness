import json

import pytest
from conftest import approve_fixture, build_package, build_to_manuscript, write

from content_harness import exporting, workflows
from content_harness.gates import claim_hash, ledger
from content_harness.state import Run
from content_harness.storage import HarnessError, atomic_write, lock, yaml_bytes


def test_end_to_end_and_restart(workspace):
    project, run = workspace
    build_package(run, project)
    recovered = Run(run.path)
    assert all(a.status == "done" for a in recovered.state.artifacts.values())
    assert not recovered.approved("publish")
    with pytest.raises(HarnessError, match="publish"):
        exporting.export(recovered, project, "wechat")
    approve_fixture(recovered, "publish")
    result = exporting.export(recovered, project, "wechat")
    assert not result["idempotent"]
    assert exporting.export(Run(run.path), project, "wechat")["idempotent"]


def test_manual_draft_edit_exact_stale_propagation(workspace):
    project, run = workspace
    build_package(run, project)
    approve_fixture(run, "publish")
    path = run.artifact_path("draft")
    atomic_write(path, path.read_bytes() + "\n用户补充。".encode())
    run.scan()
    assert run.state.artifacts["draft"].status == "in_progress"
    assert run.state.artifacts["outline"].status == "done"
    assert run.state.artifacts["brief"].status == "done"
    assert run.state.artifacts["manuscript"].status == "stale"
    assert run.state.artifacts["publish-package"].status == "stale"
    assert not run.approved("publish")
    assert "用户补充" in path.read_text()


def test_upstream_revert_does_not_resurrect_approval(workspace):
    project, run = workspace
    build_package(run, project)
    approve_fixture(run, "publish")
    path = run.artifact_path("brief")
    old = path.read_bytes()
    atomic_write(path, old + b"\nchange")
    run.scan()
    atomic_write(path, old)
    run.scan()
    run.register("brief")
    assert not run.approved("brief")
    assert not run.approved("publish")


@pytest.mark.parametrize("mode", ["missing", "corrupt", "stale"])
def test_manifest_rebuild_from_journal(workspace, mode):
    _, run = workspace
    write(run, "idea", "initial")
    path = run.path / "manifest.yaml"
    if mode == "missing":
        path.unlink()
    else:
        atomic_write(path, b"{{{{" if mode == "corrupt" else yaml_bytes({"revision": 0}))
    recovered = Run(run.path)
    assert recovered.state.artifacts["idea"].status == "done"
    assert recovered.state.revision == run.state.revision


def test_journal_committed_before_index_crash(workspace, monkeypatch):
    _, run = workspace

    def fail():
        raise OSError("simulated disk error after journal commit")

    monkeypatch.setattr(run, "index", fail)
    run.state.style_intensity = "high"
    with pytest.raises(OSError):
        run.save("interrupted")
    assert Run(run.path).state.style_intensity == "high"


def test_torn_tail_recovery_preserves_evidence(workspace):
    _, run = workspace
    with (run.path / "transitions.jsonl").open("ab") as stream:
        stream.write(b'{"partial":')
    recovered = Run(run.path)
    assert recovered.state.revision == run.state.revision
    assert len(list(run.path.glob("journal-tail-*.bin"))) == 1
    recovered.save("after-recovery")
    assert Run(run.path).state.revision == recovered.state.revision


def test_complete_corrupt_event_fails_closed(workspace):
    _, run = workspace
    with (run.path / "transitions.jsonl").open("ab") as stream:
        stream.write(b'{"partial":}\n')
    with pytest.raises(ValueError):
        Run(run.path)


def test_lock_excludes_other_writer_and_recovers(workspace):
    _, run = workspace
    with lock(run.path):
        with pytest.raises(HarnessError, match="Another writer"):
            with lock(run.path):
                pass
    with lock(run.path):
        pass


def test_workflow_pinned_and_cycle_detected(workspace):
    _, run = workspace
    value = workflows.load("wechat-longform")
    value["artifacts"]["idea"]["depends_on"] = ["draft"]
    with pytest.raises(HarnessError) as error:
        workflows.validate(value)
    assert error.value.code == "WORKFLOW_CYCLE"
    atomic_write(run.path / "workflow.yaml", yaml_bytes(value))
    with pytest.raises(HarnessError) as error:
        Run(run.path)
    assert error.value.code == "WORKFLOW_CHANGED"


def test_changed_review_cannot_reuse_old_input_hashes(workspace):
    project, run = workspace
    build_package(run, project)
    manuscript = run.artifact_path("manuscript")
    atomic_write(manuscript, manuscript.read_bytes() + b"\nnew paragraph")
    run.scan()
    run.register("manuscript")
    with pytest.raises(HarnessError) as error:
        run.register("style-report")
    assert error.value.code == "REVIEW_INPUT_CHANGED"


def test_artifact_snapshots_survive_manual_edits(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    record = run.state.artifacts["manuscript"]
    old_hash = record.registered_hash
    path = run.path / "snapshots" / old_hash.split(":")[1] / "content"
    old = path.read_bytes()
    atomic_write(run.artifact_path("manuscript"), old + b"\nedit")
    run.scan()
    assert path.read_bytes() == old
    assert record.registered_hash == old_hash
    assert record.content_hash != old_hash


def test_every_event_contains_versioned_state(workspace):
    _, run = workspace
    write(run, "idea", "test")
    rows = [json.loads(line) for line in (run.path / "transitions.jsonl").read_text().splitlines()]
    assert [r["state"]["revision"] for r in rows] == list(range(1, len(rows) + 1))


def test_status_lists_all_pending_claim_verifications(workspace):
    _, run = workspace
    write(run, "idea", "# Idea")
    write(
        run,
        "sources",
        {
            "sources": [
                {
                    "source_id": "s1",
                    "title": "Synthetic author statement",
                    "url": "https://example.com/source",
                    "accessed_at": "2026-09-18",
                    "excerpt": "The author described two experiences.",
                }
            ]
        },
    )
    atomic_write(
        run.artifact_path("claims"),
        yaml_bytes(
            {
                "claims": [
                    {
                        "claim_id": claim_id,
                        "text": f"Synthetic experience {claim_id}",
                        "type": "experience",
                        "risk": "medium",
                        "status": "author-confirmed",
                        "provenance": "Synthetic test fixture",
                    }
                    for claim_id in ["experience-one", "experience-two"]
                ]
            }
        ),
    )
    run.scan()
    report = run.report()
    assert report["human_gates"][0]["claim_ids"] == [
        "experience-one",
        "experience-two",
    ]
    claim = ledger(run).claims[0]
    run.state.claim_verifications[claim.claim_id] = claim_hash(claim, run.hash("sources"))
    assert run.report()["human_gates"][0]["claim_ids"] == ["experience-two"]
