"""Smoke-check an installed wheel in an independent temporary content project."""

import json
import subprocess
import tempfile
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory(prefix="content-harness-smoke-") as directory:
        root = Path(directory)
        for args in [
            ["version"],
            ["check-workflow", "wechat-longform"],
            [
                "init",
                str(root),
                "--preset",
                "wiki",
                "--output-dir",
                "知识库/我的文章",
                "--target",
                "library",
                "--scenario",
                "work-habits",
            ],
            [
                "--project",
                str(root),
                "configure",
                "--read-root",
                "原始资料",
                "--output-dir",
                "成品/{scenario}/{date}/{slug}",
            ],
            ["--project", str(root), "doctor"],
            ["install-skills", "--client", "codex", "--destination", str(root / "skills")],
        ]:
            result = subprocess.run(
                ["content-harness", *args], cwd=root, text=True, capture_output=True, check=True
            )
            assert json.loads(result.stdout)["ok"]
        result = subprocess.run(
            ["content-harness", "--project", str(root), "configure"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        config = json.loads(result.stdout)["profile"]
        assert config["default_target"] == "library"
        assert config["exports"]["library"]["directory"] == "成品/{scenario}/{date}/{slug}"
        assert config["style"]["default_scenario"] == "work-habits"
        assert config["read_roots"] == ["原始资料"]
        skills = list((root / "skills").glob("*/SKILL.md"))
        assert len(skills) == 13
        # The new run gate must remain closed on a fresh installed project.
        result = subprocess.run(
            ["content-harness", "--project", str(root), "new", "demo"],
            cwd=root,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 1 and "AUTHOR_CONFIRMATION_REQUIRED" in result.stdout
        print(
            "Installed-wheel smoke: 13 skills, workflow, custom paths/scenario, doctor and author gate passed"
        )


if __name__ == "__main__":
    main()
