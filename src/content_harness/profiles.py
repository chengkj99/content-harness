from pathlib import Path
from string import Formatter

from .storage import (
    atomic_write,
    digest,
    identifier,
    lock,
    read_yaml,
    require,
    safe_path,
    yaml_bytes,
)

RESERVED = {".git", ".content-harness", ".agents", ".codex", ".claude", ".cursor"}


def output_path(project, template, run_id, scenario):
    require(
        isinstance(template, str) and bool(template.strip()),
        "INVALID_PROFILE",
        "empty output directory",
    )
    values = {"run_id": run_id, "date": run_id[:10], "slug": run_id[11:], "scenario": scenario}
    for _, field, spec, conversion in Formatter().parse(template):
        require(
            field is None or (field in values and not spec and not conversion),
            "INVALID_OUTPUT_TEMPLATE",
            "Use {run_id}, {date}, {slug} or {scenario}",
        )
    relative = template.format(**values)
    path = safe_path(project, relative)
    require(not RESERVED.intersection(Path(relative).parts), "EXPORT_FORBIDDEN", relative)
    return path


def output_template(directory):
    require(bool(directory.strip()), "INVALID_OUTPUT_TEMPLATE", "empty directory")
    return directory if "{" in directory else directory.rstrip("/") + "/{run_id}"


def validate_profile(project, value):
    require(
        isinstance(value, dict) and value.get("schema_version") == 1,
        "INVALID_PROFILE",
        "schema_version",
    )
    require(isinstance(value.get("workflow"), str), "INVALID_PROFILE", "workflow")
    identifier(value["workflow"])
    require(
        value.get("run_root") == ".content-harness/runs",
        "INVALID_PROFILE",
        "Internal run_root stays .content-harness/runs",
    )
    authors = value.get("author_sources")
    require(
        isinstance(authors, list) and len(authors) == 1,
        "INVALID_PROFILE",
        "Choose one author profile per project",
    )
    for field in ["read_roots", "dedupe_roots", "policy_files", "author_sources"]:
        paths = value.get(field, [])
        require(isinstance(paths, list), "INVALID_PROFILE", field)
        for path in paths:
            require(isinstance(path, str) and bool(path.strip()), "INVALID_PROFILE", field)
            safe_path(project, path)
    exports = value.get("exports")
    require(isinstance(exports, dict) and bool(exports), "INVALID_PROFILE", "exports")
    for name, target in exports.items():
        identifier(name)
        require(isinstance(target, dict) and "directory" in target, "INVALID_PROFILE", name)
        output_path(project, target["directory"], "2026-01-01-example", "example")
    require(
        value.get("default_target", next(iter(exports))) in exports,
        "INVALID_PROFILE",
        "default_target",
    )
    require(isinstance(value.get("style"), dict), "INVALID_PROFILE", "style")
    style = value["style"]
    identifier(style.get("default_scenario", value["workflow"]))
    references = style.get("reference_files", [])
    require(isinstance(references, list), "INVALID_PROFILE", "style.reference_files")
    for path in references:
        require(isinstance(path, str) and bool(path.strip()), "INVALID_PROFILE", path)
        safe_path(project, path)
    scenarios = style.get("scenarios", {})
    require(isinstance(scenarios, dict), "INVALID_PROFILE", "style.scenarios")
    for scenario, preset in scenarios.items():
        identifier(scenario)
        require(isinstance(preset, dict), "INVALID_PROFILE", f"style.scenarios.{scenario}")
        scene = preset.get("scene")
        require(scene is None or isinstance(scene, str), "INVALID_PROFILE", f"{scenario}.scene")
        if scene:
            identifier(scene)
        polish = preset.get("polish", [])
        require(isinstance(polish, list), "INVALID_PROFILE", f"{scenario}.polish")
        for style_id in polish:
            identifier(style_id)
    return value


def init(project: Path, workflow: str, preset: str, **options):
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
            "read_roots": [] if preset == "wiki" else ["materials"],
            "dedupe_roots": ["content"],
            "policy_files": [p for p in ["AGENTS.md", "SCHEMA.md"] if (project / p).is_file()],
            "exports": {"wechat": {"directory": "content/{run_id}"}},
            "default_target": "wechat",
            "style": {
                "default_scene": None,
                "default_polish": [],
                "allow_run_override": True,
                "default_scenario": workflow,
                "reference_files": [],
                "scenarios": {},
            },
            "write_policy": {"publish": "disabled", "export_conflict": "fail"},
        }
        apply_options(profile, **options)
        validate_profile(project, profile)
        author = safe_path(project, profile["author_sources"][0])
        require(not author.exists() or author.is_file(), "INVALID_PROFILE", "author file")
        atomic_write(path, yaml_bytes(profile))
        if not author.exists():
            atomic_write(
                author,
                "# 作者资料\n\n请填写真实的受众、表达习惯与不允许编造的经历边界。\n".encode(),
            )
        atomic_write(
            root / ".gitignore",
            b"runs/\narchive/\nstyle-memory/\nauthor-profile.md\nauthor-confirmation.yaml\n.lock\n",
        )
        atomic_write(root / "style-memory/author.yaml", yaml_bytes({"version": 0, "rules": []}))
        ensure_scenario(project, profile["style"]["default_scenario"])
    return profile


def apply_options(
    value,
    output_dir=None,
    target=None,
    read_roots=None,
    dedupe_roots=None,
    policy_files=None,
    author_file=None,
    scenario=None,
    reference_files=None,
    scene_style=None,
    polish_styles=None,
):
    selected = target or value.get("default_target", next(iter(value["exports"])))
    identifier(selected)
    if output_dir is not None:
        value["exports"][selected] = {"directory": output_template(output_dir)}
    require(selected in value["exports"], "EXPORT_UNKNOWN", "New target requires --output-dir")
    value["default_target"] = selected
    for key, paths in [
        ("read_roots", read_roots),
        ("dedupe_roots", dedupe_roots),
        ("policy_files", policy_files),
    ]:
        if paths is not None:
            value[key] = list(dict.fromkeys(paths))
    if author_file is not None:
        value["author_sources"] = [author_file]
    if scenario is not None:
        value["style"]["default_scenario"] = identifier(scenario)
    if reference_files is not None:
        value["style"]["reference_files"] = list(dict.fromkeys(reference_files))
    if scene_style is not None or polish_styles is not None:
        scenario_id = identifier(scenario or value["style"].get("default_scenario", value["workflow"]))
        preset = value["style"].setdefault("scenarios", {}).setdefault(scenario_id, {})
        if scene_style is not None:
            preset["scene"] = identifier(scene_style) if scene_style else None
        if polish_styles is not None:
            preset["polish"] = list(dict.fromkeys(polish_styles))


def configure(project, **options):
    root = safe_path(project, ".content-harness")
    with lock(root):
        path = root / "project.yaml"
        before = path.read_bytes()
        value = validate_profile(project, read_yaml(path))
        apply_options(value, **options)
        validate_profile(project, value)
        require(
            safe_path(project, value["author_sources"][0]).is_file(),
            "AUTHOR_FILE_MISSING",
            "Create the author file before configuring it",
        )
        require(path.read_bytes() == before, "CONFLICT_EXTERNAL_EDIT", "project.yaml")
        if options.get("scenario"):
            ensure_scenario(project, options["scenario"])
        atomic_write(path, yaml_bytes(value))
        return value


def ensure_scenario(project, scenario):
    identifier(scenario)
    root = safe_path(project, ".content-harness/style-memory")
    with lock(root):
        path = safe_path(root, f"scenarios/{scenario}.yaml")
        if not path.exists():
            atomic_write(path, yaml_bytes({"version": 0, "rules": []}))


def project_root(start: Path):
    start = start.resolve()
    for path in [start, *start.parents]:
        if (path / ".content-harness/project.yaml").exists():
            return path
    require(False, "PROJECT_NOT_FOUND", "Run content-harness init . first")


def profile(project):
    value = read_yaml(safe_path(project, ".content-harness/project.yaml"))
    return validate_profile(project, value)


def author_path(project):
    return safe_path(project, profile(project)["author_sources"][0])


def author_hash(project):
    return digest(author_path(project).read_bytes())


def author_confirmed(project):
    path = safe_path(project, ".content-harness/author-confirmation.yaml")
    return path.exists() and read_yaml(path).get("content_hash") == author_hash(project)


def scenario_preset(config, scenario):
    style = config["style"]
    preset = style.get("scenarios", {}).get(scenario, {})
    return {
        "scene": preset.get("scene", style.get("default_scene")),
        "polish": preset.get("polish", style.get("default_polish", [])),
    }
