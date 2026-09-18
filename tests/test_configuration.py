import json
from pathlib import Path

import pytest
from conftest import approve_fixture, build_package, build_to_manuscript
from typer.testing import CliRunner

from content_harness import exporting, profiles, styles
from content_harness.cli import app
from content_harness.state import Run
from content_harness.storage import HarnessError, atomic_write, digest, read_yaml, yaml_bytes

runner = CliRunner()


def test_wiki_init_does_not_impose_private_layout(tmp_path):
    value = profiles.init(tmp_path, "wechat-longform", "wiki")
    assert value["read_roots"] == []
    assert value["exports"]["wechat"]["directory"] == "content/{run_id}"
    assert "raw/studio" not in json.dumps(value)


def test_cli_configures_chinese_paths_and_named_destination(tmp_path):
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--preset",
            "wiki",
            "--output-dir",
            "知识库/我的文章",
            "--target",
            "library",
            "--read-root",
            "原始资料/读书笔记",
            "--read-root",
            "素材 收集",
            "--dedupe-root",
            "旧文章",
            "--scenario",
            "book-notes",
        ],
    )
    assert result.exit_code == 0, result.output
    value = profiles.profile(tmp_path)
    assert value["exports"]["library"]["directory"] == "知识库/我的文章/{run_id}"
    assert value["default_target"] == "library"
    assert value["read_roots"] == ["原始资料/读书笔记", "素材 收集"]
    assert value["style"]["default_scenario"] == "book-notes"


@pytest.mark.parametrize(
    "directory",
    ["wiki/articles", "知识库/文章", "成品 归档/{date}/{slug}", "交付/{scenario}/{run_id}"],
)
def test_custom_export_succeeds_without_overwriting(workspace, directory):
    project, run = workspace
    build_package(run, project)
    approve_fixture(run, "publish")
    profiles.configure(project, output_dir=directory, target="library")
    result = exporting.export(run, project)
    assert result["path"].startswith(str(project))
    assert exporting.export(run, project)["idempotent"]
    assert run.state.exports


@pytest.mark.parametrize(
    "directory",
    [
        "../outside",
        "/tmp/outside",
        ".git/hooks",
        "content/.git/hooks",
        ".agents/skills",
        "{run_id.__class__}",
        "{unknown}",
        "{date!r}",
        "{slug:>20}",
    ],
)
def test_invalid_configuration_does_not_change_profile(workspace, directory):
    project, _ = workspace
    path = project / ".content-harness/project.yaml"
    before = path.read_bytes()
    with pytest.raises((HarnessError, ValueError)):
        profiles.configure(project, output_dir=directory)
    assert path.read_bytes() == before


def test_configuration_changes_do_not_move_old_export(workspace):
    project, run = workspace
    build_package(run, project)
    approve_fixture(run, "publish")
    old = exporting.export(run, project)
    profiles.configure(project, output_dir="新目录")
    new = exporting.export(run, project)
    assert old["path"] != new["path"]
    assert (Path(old["path"]) / "article.md").is_file()


def test_author_file_reused_without_overwrite(tmp_path):
    author = tmp_path / "关于我.md"
    atomic_write(author, "真实资料".encode())
    profiles.init(tmp_path, "wechat-longform", "default", author_file="关于我.md")
    assert profiles.author_path(tmp_path) == author
    assert author.read_text() == "真实资料"


def test_author_profile_change_invalidates_confirmation(workspace):
    project, _ = workspace
    atomic_write(project / "作者.md", "另一份作者边界".encode())
    profiles.configure(project, author_file="作者.md")
    assert not profiles.author_confirmed(project)


def test_new_scenario_frozen_independent_of_workflow(workspace):
    project, _ = workspace
    profiles.configure(project, scenario="newsletter")
    result = runner.invoke(app, ["--project", str(project), "new", "independent"])
    assert result.exit_code == 0, result.output
    path = json.loads(result.output)["path"]
    run = Run(Path(path))
    assert run.state.scenario == "newsletter"
    assert run.state.workflow == "wechat-longform"
    build_to_manuscript(run, project)
    spec = read_yaml(run.artifact_path("style-spec"))
    assert spec["memory_snapshot"]["scenario_id"] == "newsletter"
    profiles.configure(project, scenario="product-notes")
    run.scan()
    assert run.state.scenario == "newsletter"
    assert run.state.artifacts["style-spec"].status == "done"
    manuscript = run.artifact_path("manuscript")
    atomic_write(manuscript, manuscript.read_bytes() + b"\nedit")
    run.scan()
    lesson = styles.feedback(run, project, "manuscript", "scenario", "scope")
    assert lesson["scenario"] == "newsletter"


def test_scenario_preset_selects_scene_and_polish(workspace):
    project, _ = workspace
    profiles.configure(
        project,
        scenario="personal-essay",
        scene_style="personal-narrative-zh",
        polish_styles=["natural-human-zh"],
    )
    result = runner.invoke(app, ["--project", str(project), "new", "personal"])
    assert result.exit_code == 0, result.output
    run = Run(Path(json.loads(result.output)["path"]))
    assert run.state.scenario == "personal-essay"
    assert run.state.style_selection == ["personal-narrative-zh", "natural-human-zh"]


def test_cli_configure_rejects_unknown_style_before_writing(workspace):
    project, _ = workspace
    path = project / ".content-harness/project.yaml"
    before = path.read_bytes()
    result = runner.invoke(
        app,
        [
            "--project",
            str(project),
            "configure",
            "--scenario",
            "personal-essay",
            "--scene-style",
            "missing-style",
        ],
    )
    assert result.exit_code == 1
    assert "STYLE_UNKNOWN" in result.output
    assert path.read_bytes() == before


def test_cli_configure_replaces_lists_and_can_clear(workspace):
    project, _ = workspace
    base = ["--project", str(project), "configure"]
    result = runner.invoke(
        app, base + ["--read-root", "素材", "--read-root", "笔记", "--policy-file", "编辑规范.md"]
    )
    assert result.exit_code == 0, result.output
    assert profiles.profile(project)["read_roots"] == ["素材", "笔记"]
    result = runner.invoke(app, base + ["--clear-read-roots", "--clear-dedupe-roots"])
    assert result.exit_code == 0, result.output
    assert profiles.profile(project)["read_roots"] == []
    assert profiles.profile(project)["dedupe_roots"] == []


def test_legacy_profile_and_run_remain_readable(workspace):
    project, run = workspace
    path = project / ".content-harness/project.yaml"
    value = read_yaml(path)
    value.pop("default_target")
    value["style"].pop("default_scenario")
    value["exports"]["wechat"]["directory"] = "legacy/output/{run_id}"
    atomic_write(path, yaml_bytes(value))
    build_package(run, project)
    approve_fixture(run, "publish")
    assert "legacy/output" in exporting.export(run, project)["path"]
    assert Run(run.path).state.scenario is None


def test_author_named_scenario_has_separate_version_history(workspace):
    project, _ = workspace
    profiles.ensure_scenario(project, "author")
    root = project / ".content-harness/style-memory"
    author = root / "author.yaml"
    scene = root / "scenarios/author.yaml"
    author_old = {"version": 0, "rules": [{"rule": "author-only"}]}
    scene_old = {"version": 0, "rules": [{"rule": "scene-only"}]}
    styles.save_version(root, author, author_old)
    styles.save_version(root, scene, scene_old)
    atomic_write(scene, yaml_bytes({"version": 1, "rules": []}))
    result = styles.rollback(project, "scenario", "author", 0, digest(scene.read_bytes()))
    assert result["rules"] == scene_old["rules"]
    assert read_yaml(root / "versions/author/0.yaml") == author_old


def test_legacy_scenario_history_can_be_restored(workspace):
    project, _ = workspace
    root = project / ".content-harness/style-memory"
    scene = root / "scenarios/wechat-longform.yaml"
    old = {"version": 0, "rules": [{"rule": "legacy"}]}
    atomic_write(root / "versions/wechat-longform/0.yaml", yaml_bytes(old))
    atomic_write(scene, yaml_bytes({"version": 1, "rules": []}))
    result = styles.rollback(project, "scenario", "wechat-longform", 0, digest(scene.read_bytes()))
    assert result["rules"] == old["rules"]
