from pathlib import Path

from .storage import atomic_write, digest, lock, read_yaml, require, safe_path, yaml_bytes


def init(project: Path, workflow: str, preset: str):
    project = project.resolve()
    root = safe_path(project, ".content-harness")
    with lock(root):
        path = safe_path(root, "project.yaml")
        require(not path.exists(), "PROJECT_EXISTS", str(path))
        profile = {
            "schema_version": 1,
            "workflow": workflow,
            "run_root": ".content-harness/runs",
            "author_sources": [".content-harness/author-profile.md"],
            "read_roots": ["raw", "wiki"] if preset == "wiki" else ["materials"],
            "dedupe_roots": ["raw/studio/funnel/formatted/wechat"]
            if preset == "wiki"
            else ["content"],
            "policy_files": ["AGENTS.md", "SCHEMA.md"],
            "exports": {
                "wechat": {
                    "directory": "raw/studio/funnel/formatted/wechat/{run_id}"
                    if preset == "wiki"
                    else "content/{run_id}"
                }
            },
            "style": {"default_scene": None, "default_polish": [], "allow_run_override": True},
            "write_policy": {"publish": "disabled", "export_conflict": "fail"},
        }
        atomic_write(path, yaml_bytes(profile))
        atomic_write(
            root / "author-profile.md",
            "# 作者资料\n\n请填写真实的受众、表达习惯与不允许编造的经历边界。\n".encode(),
        )
        atomic_write(
            root / ".gitignore",
            b"runs/\narchive/\nstyle-memory/\nauthor-profile.md\nauthor-confirmation.yaml\n.lock\n",
        )
        for relative in [
            "style-memory/author.yaml",
            "style-memory/scenarios/wechat-longform.yaml",
            "style-memory/scenarios/technical-tutorial.yaml",
            "style-memory/scenarios/story-essay.yaml",
        ]:
            atomic_write(root / relative, yaml_bytes({"version": 0, "rules": []}))
    return profile


def project_root(start: Path):
    start = start.resolve()
    for path in [start, *start.parents]:
        if (path / ".content-harness/project.yaml").exists():
            return path
    require(False, "PROJECT_NOT_FOUND", "Run content-harness init . first")


def profile(project):
    value = read_yaml(safe_path(project, ".content-harness/project.yaml"))
    require(value.get("schema_version") == 1, "INVALID_PROFILE", "schema_version")
    require(
        value.get("run_root") == ".content-harness/runs",
        "INVALID_PROFILE",
        "M1 uses fixed run_root",
    )
    require(
        value.get("author_sources") == [".content-harness/author-profile.md"],
        "INVALID_PROFILE",
        "M1 uses one author profile",
    )
    for field in ["read_roots", "dedupe_roots", "policy_files", "author_sources"]:
        for path in value.get(field, []):
            safe_path(project, path)
    return value


def author_hash(project):
    return digest(safe_path(project, ".content-harness/author-profile.md").read_bytes())


def author_confirmed(project):
    path = safe_path(project, ".content-harness/author-confirmation.yaml")
    return path.exists() and read_yaml(path).get("content_hash") == author_hash(project)
