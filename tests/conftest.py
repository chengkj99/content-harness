import uuid

import pytest

from content_harness import exporting, profiles, styles, workflows
from content_harness.models import Approval
from content_harness.state import Run
from content_harness.storage import atomic_write, now, read_yaml, yaml_bytes


def write(run, name, data):
    atomic_write(
        run.artifact_path(name), data.encode() if isinstance(data, str) else yaml_bytes(data)
    )
    run.scan()
    run.register(name)


def approve_fixture(run, gate):
    """Test-only approval injection; never shipped as a CLI bypass."""
    name = run.workflow["gates"][gate]
    record = run.state.artifacts[name]
    run.state.approvals.append(
        Approval(
            approval_id=uuid.uuid4().hex,
            at=now(),
            gate=gate,
            artifact=name,
            content_hash=record.content_hash,
            artifact_revision=record.revision,
        )
    )
    run.save("test-fixture-approval")


def input_hashes(run, name):
    return {
        dep: run.state.artifacts[dep].content_hash
        for dep in run.workflow["artifacts"][name]["depends_on"]
    }


def build_to_brief(run):
    project = run.path.parents[2]
    write(run, "idea", "# 想法\n怎样让一次写作有可检查的交付？")
    write(
        run,
        "sources",
        {
            "sources": [
                {
                    "source_id": "s1",
                    "title": "Synthetic fixture",
                    "url": "https://example.com/fixture",
                    "accessed_at": "2026-09-08",
                    "excerpt": "This is synthetic test evidence, not research.",
                }
            ]
        },
    )
    write(
        run,
        "claims",
        {
            "claims": [
                {
                    "claim_id": "c1",
                    "text": "在当前样本中，可能减少 2 次遗漏。",
                    "type": "observation",
                    "risk": "low",
                    "status": "bounded",
                    "boundary": "仅限合成测试",
                    "protected_terms": ["当前样本"],
                }
            ]
        },
    )
    styles.compile_voice_contract(run, project)
    write(
        run,
        "brief",
        "---\naudience: 内容作者\nquestion: 如何交付\nthesis: 可检查的过程\nboundaries: 合成演示\naction: 建立一项检查\ndedupe: 独立测试\n---\n# 简报\n仅为测试。",
    )


def build_to_manuscript(run, project, selection=None):
    if selection is not None:
        run.state.style_selection = list(selection)
        run.save("test-style-selection")
    build_to_brief(run)
    approve_fixture(run, "brief")
    styles.compile_style(run, project, run.state.style_selection, "medium")
    write(run, "outline", "# 提纲\n先列出检查对象，再保存检查结果。")
    draft = "# 可检查的交付\n\n在当前样本中，可能减少 2 次遗漏。<!-- claim:c1 -->\n\n先选一个需要检查的对象。\n"
    write(run, "draft", draft)
    write(run, "manuscript", draft)


def build_reviews(run):
    spec = read_yaml(run.artifact_path("style-spec"))
    selected = [
        item["id"]
        for layer in ("scene", "polish")
        for item in spec["style_stack"].get(layer, [])
    ]
    write(
        run,
        "style-report",
        {
            "input_hashes": input_hashes(run, "style-report"),
            "changes": [],
            "rejected": [],
            "fidelity": "pass",
            "reason": "Synthetic unchanged draft",
            "rule_assessments": [
                {
                    "style_id": style_id,
                    "status": "already-satisfied",
                    "evidence": "Synthetic fixture body",
                }
                for style_id in selected
            ],
        },
    )
    for name in ["fact-review", "editorial-review"]:
        write(
            run,
            name,
            {
                "input_hashes": input_hashes(run, name),
                "verdict": "pass",
                "summary": "Synthetic fixture assessment",
                "findings": [],
                "fidelity": "pass",
                "assessments": [
                    {
                        "claim_id": "c1",
                        "support": "not-applicable",
                        "reason": "Bounded synthetic observation",
                    }
                ]
                if name == "fact-review"
                else [],
            },
        )
    contract = read_yaml(run.artifact_path("voice-contract"))
    voice_dimensions = list(contract["required_dimensions"])
    configured_styles = [
        item
        for layer in ("scene", "polish")
        for item in spec["style_stack"].get(layer, [])
    ]
    for item in configured_styles:
        voice_dimensions.extend(item.get("dimensions", []))
    voice_dimensions = list(dict.fromkeys(voice_dimensions))
    requires_signature = contract["requires_signature"] or any(
        item.get("requires_signature", False) for item in configured_styles
    )
    write(
        run,
        "voice-review",
        {
            "input_hashes": input_hashes(run, "voice-review"),
            "verdict": "pass",
            "summary": "Synthetic voice assessment",
            "fidelity": "pass",
            "assessments": [
                {
                    "dimension": dimension,
                    "score": 3,
                    "location": "Synthetic fixture body",
                    "evidence": "Fixture evidence",
                    "reason": "Fixture satisfies the configured minimum",
                }
                for dimension in voice_dimensions
            ],
            "signature_passage": "Synthetic author-specific passage"
            if requires_signature
            else None,
            "genericity_test": {
                "result": "pass",
                "reason": "Synthetic fixture explicitly identifies its test context",
            },
            "findings": [],
        },
    )


def build_package(run, project):
    build_to_manuscript(run, project)
    build_reviews(run)
    for name in ["visual-plan", "visual-assets"]:
        write(run, name, {"images": [], "no_images_reason": "Text-only synthetic example"})
    titles, summary = project / "titles.txt", project / "summary.txt"
    atomic_write(titles, "可检查的交付\n".encode())
    atomic_write(summary, "建立明确的检查对象。\n".encode())
    exporting.package(run, titles, summary, "missing")


@pytest.fixture
def workspace(tmp_path):
    profiles.init(tmp_path, "wechat-longform", "default")
    atomic_write(
        tmp_path / ".content-harness/author-profile.md", "匿名合成测试作者。不得虚构经历。".encode()
    )
    atomic_write(
        tmp_path / ".content-harness/author-confirmation.yaml",
        yaml_bytes({"content_hash": profiles.author_hash(tmp_path)}),
    )
    path = tmp_path / ".content-harness/runs/2026-09-08-test"
    path.mkdir(parents=True)
    run = Run.create(path, "2026-09-08-test", workflows.load("wechat-longform"), [], "medium")
    return tmp_path, run
