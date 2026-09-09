import re
from pathlib import Path

import pytest
from conftest import approve_fixture, build_reviews, build_to_manuscript, write

from content_harness import exporting, workflows
from content_harness.storage import HarnessError, atomic_write, read_yaml, yaml_bytes


def test_all_skill_links_resolve():
    root = workflows.resources() / "skills"
    for path in root.rglob("*.md"):
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if not target.startswith("http"):
                assert (path.parent / target).resolve().is_file(), (path, target)


def test_public_document_links_resolve():
    root = Path(__file__).resolve().parents[1]
    for path in [root / "README.md", *sorted((root / "docs").glob("*.md"))]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if target.startswith(("http:", "https:", "#")):
                continue
            target = target.split("#", 1)[0]
            assert (path.parent / target).resolve().is_file(), (path, target)


def test_skill_contracts_do_not_depend_on_private_skills():
    root = workflows.resources()
    for path in root.rglob("*"):
        if path.is_file():
            text = path.read_text()
            assert "/Users/" not in text
            assert "kangjian-skill" not in text
            assert "kj-skills" not in text
    for path in (root / "skills").glob("*/SKILL.md"):
        assert "description:" in path.read_text()
        assert "Agent 不得自行执行 approve" in path.read_text()


def image_plan():
    return {
        "images": [
            {
                "path": "assets/flow.svg",
                "alt": "从问题到检查的流程图",
                "purpose": "说明输入与输出",
                "source": "original synthetic fixture",
                "license": "CC0",
                "location": "文章末尾",
            }
        ]
    }


def test_full_image_package(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    atomic_write(
        run.path / "artifacts/assets/flow.svg",
        b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="80"><text x="10" y="30">Input to output</text></svg>',
    )
    build_reviews(run)
    write(run, "visual-plan", image_plan())
    write(run, "visual-assets", image_plan())
    atomic_write(project / "titles.txt", "一次明确的检查".encode())
    atomic_write(project / "summary.txt", "从输入到输出的流程。".encode())
    exporting.package(run, project / "titles.txt", project / "summary.txt", "missing")
    approve_fixture(run, "publish")
    result = exporting.export(run, project, "wechat")
    assert (Path(result["path"]) / "assets/flow.svg").is_file()
    assert (
        "![从问题到检查的流程图](assets/flow.svg)"
        in (Path(result["path"]) / "article.md").read_text()
    )


@pytest.mark.parametrize(
    "data", [b"<svg><script>alert(1)</script></svg>", b'<svg onload="alert(1)"/>', b"not an image"]
)
def test_unsafe_or_broken_images_fail(workspace, data):
    project, run = workspace
    build_to_manuscript(run, project)
    build_reviews(run)
    write(run, "visual-plan", image_plan())
    atomic_write(run.path / "artifacts/assets/flow.svg", data)
    atomic_write(run.artifact_path("visual-assets"), yaml_bytes(image_plan()))
    run.scan()
    with pytest.raises(HarnessError):
        run.register("visual-assets")


def test_deleted_image_cannot_keep_done(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    build_reviews(run)
    write(run, "visual-plan", image_plan())
    atomic_write(
        run.path / "artifacts/assets/flow.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    )
    write(run, "visual-assets", image_plan())
    (run.path / "artifacts/assets/flow.svg").unlink()
    run.scan()
    with pytest.raises(HarnessError) as error:
        run.register("visual-assets")
    assert error.value.code == "IMAGE_MISSING"


def test_rejected_semantic_report_blocks(workspace):
    project, run = workspace
    build_to_manuscript(run, project)
    build_reviews(run)
    data = read_yaml(run.artifact_path("fact-review"))
    data["findings"] = [
        {
            "location": "para 1",
            "reason": "meaning drift",
            "fix": "restore claim",
            "severity": "blocker",
        }
    ]
    atomic_write(run.artifact_path("fact-review"), yaml_bytes(data))
    run.scan()
    with pytest.raises(HarnessError) as error:
        run.register("fact-review")
    assert error.value.code == "REVIEW_BLOCKED"
