from importlib.resources import files

from .storage import identifier, read_yaml, require


def resources():
    return files("content_harness").joinpath("resources")


CHECKERS = {
    "text",
    "sources",
    "claims",
    "brief",
    "style",
    "draft",
    "manuscript",
    "style-report",
    "fact-review",
    "review",
    "visual-plan",
    "visual-assets",
    "package",
}


def validate(workflow):
    require(workflow.get("schema_version") == 1, "INVALID_WORKFLOW", "schema_version")
    definitions = workflow["artifacts"]
    order, visiting = [], set()

    def visit(name):
        require(name in definitions, "INVALID_WORKFLOW", f"unknown dependency: {name}")
        require(name not in visiting, "WORKFLOW_CYCLE", name)
        if name in order:
            return
        visiting.add(name)
        item = definitions[name]
        require(item["check"] in CHECKERS, "INVALID_WORKFLOW", name)
        skill = resources() / "skills" / item["skill"] / "SKILL.md"
        require(skill.is_file(), "SKILL_MISSING", item["skill"])
        for dep in item["depends_on"]:
            visit(dep)
        visiting.remove(name)
        order.append(name)

    for name in definitions:
        visit(name)
    for gate, artifact in workflow["gates"].items():
        require(artifact in definitions, "INVALID_WORKFLOW", gate)
    for name, item in definitions.items():
        require(not item.get("gate") or item["gate"] in workflow["gates"], "INVALID_WORKFLOW", name)
    paths = [item["path"] for item in definitions.values()]
    require(len(paths) == len(set(paths)), "INVALID_WORKFLOW", "duplicate paths")
    return order


def load(workflow_id):
    identifier(workflow_id)
    path = resources() / "workflows" / workflow_id / "workflow.yaml"
    require(path.is_file(), "WORKFLOW_UNKNOWN", workflow_id)
    workflow = read_yaml(path)
    validate(workflow)
    return workflow
