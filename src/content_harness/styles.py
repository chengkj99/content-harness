import difflib
import uuid

from .models import Feedback
from .profiles import author_confirmed, profile
from .storage import (
    atomic_write,
    digest,
    identifier,
    json_bytes,
    lock,
    now,
    read_yaml,
    require,
    safe_path,
    yaml_bytes,
)
from .workflows import resources


def pack(style_id):
    identifier(style_id)
    root = resources() / "styles" / style_id
    require((root / "rubric.yaml").is_file(), "STYLE_UNKNOWN", style_id)
    return {**read_yaml(root / "rubric.yaml"), "rules": (root / "STYLE.md").read_text()}


def compile_style(run, project, selection, intensity):
    require(run.approved("brief"), "APPROVAL_REQUIRED", "brief")
    require(author_confirmed(project), "AUTHOR_CONFIRMATION_REQUIRED", "confirm-author")
    require(intensity in {"low", "medium", "high"}, "INVALID_INTENSITY", intensity)
    config = profile(project)
    require(
        config["style"].get("allow_run_override", True) or selection == run.state.style_selection,
        "STYLE_OVERRIDE_DISABLED",
        "project profile",
    )
    stack = {"author": {}, "scene": [], "polish": []}
    for style_id in dict.fromkeys(selection):
        item = pack(style_id)
        if item["layer"] != "base":
            stack[item["layer"]].append(item)
    memory_root = safe_path(project, ".content-harness/style-memory")
    with lock(memory_root):
        author = read_yaml(safe_path(memory_root, "author.yaml"))
        scenario = read_yaml(safe_path(memory_root, f"scenarios/{run.state.workflow}.yaml"))
        author_text = safe_path(project, ".content-harness/author-profile.md").read_text()
        memory = {"author": author, "scenario": scenario, "author_profile": author_text}
    stack["author"] = {
        "id": "project-author",
        "version": author["version"],
        "rules": author["rules"],
        "profile": author_text,
    }
    spec = {
        "schema_version": 1,
        "base": pack("neutral"),
        "style_stack": stack,
        "memory_snapshot": {
            "scenario": run.state.workflow,
            "content_hash": digest(json_bytes(memory)),
            **memory,
        },
        "intensity": intensity,
        "apply_to": {
            "outline": ["hook", "pacing"],
            "draft": ["examples", "reader_context"],
            "polish": ["sentence_rhythm", "remove_cliches"],
        },
        "protected": [
            "claims",
            "numbers_and_units",
            "quotes",
            "qualifiers",
            "confirmed_experience",
        ],
    }
    # Explicit style changes preserve the old registered revision in snapshots.
    record = run.state.artifacts["style-spec"]
    require(
        record.content_hash == record.registered_hash or record.content_hash is None,
        "CONFLICT_EXTERNAL_EDIT",
        "style-spec has unregistered manual edits; preserve them before recompiling",
    )
    run.state.style_selection, run.state.style_intensity = selection, intensity
    atomic_write(safe_path(run.path, "style-compiled.yaml"), yaml_bytes(spec))
    atomic_write(run.artifact_path("style-spec"), yaml_bytes(spec))
    run.scan()
    run.register("style-spec")
    return spec


def feedback(run, project, artifact, scope, reason):
    require(scope in {"run", "author", "scenario"}, "INVALID_SCOPE", scope)
    require(artifact in {"draft", "manuscript"}, "INVALID_ARTIFACT", artifact)
    before_hash = run.state.artifacts[artifact].registered_hash
    require(bool(before_hash), "SNAPSHOT_MISSING", "Register an initial revision first")
    before = safe_path(run.path, "snapshots/" + before_hash.split(":")[1] + "/content").read_text()
    after = run.artifact_path(artifact).read_text()
    require(before != after, "NO_STYLE_DIFF", "Record feedback before checking the edited artifact")
    lesson = Feedback(
        lesson_id="lesson-" + uuid.uuid4().hex[:12],
        run_id=run.state.run_id,
        artifact=artifact,
        scope=scope,
        scenario=run.state.workflow,
        reason=reason,
        before_hash=before_hash,
        after_hash=run.hash(artifact),
        diff="".join(
            difflib.unified_diff(
                before.splitlines(True),
                after.splitlines(True),
                fromfile="registered",
                tofile="edited",
            )
        ),
    )
    root = safe_path(project, ".content-harness/style-memory")
    with lock(root):
        atomic_write(
            safe_path(root, f"candidates/{lesson.lesson_id}.yaml"), yaml_bytes(lesson.model_dump())
        )
    run.save("style-feedback:" + lesson.lesson_id)
    return lesson.model_dump()


def memory_target(root, scope, scenario):
    require(
        scope in {"author", "scenario"}, "INVALID_SCOPE", "Long-term memory: author or scenario"
    )
    identifier(scenario)
    path = safe_path(root, "author.yaml" if scope == "author" else f"scenarios/{scenario}.yaml")
    require(path.is_file(), "SCENARIO_UNKNOWN", scenario)
    return path


def promote(project, run_id, lesson_id, expected_hash):
    root = safe_path(project, ".content-harness/style-memory")
    identifier(lesson_id)
    with lock(root):
        path = safe_path(root, f"candidates/{lesson_id}.yaml")
        require(digest(path.read_bytes()) == expected_hash, "CONFLICT_EXTERNAL_EDIT", lesson_id)
        lesson = Feedback.model_validate(read_yaml(path))
        require(
            lesson.run_id == run_id and lesson.status == "candidate", "INVALID_LESSON", lesson_id
        )
        require(
            bool(lesson.proposed_rule.strip()) and bool(lesson.eval_proposal.strip()),
            "LESSON_INCOMPLETE",
            "rule and eval required",
        )
        target = memory_target(root, lesson.scope, lesson.scenario)
        current = read_yaml(target)
        if any(r["lesson_id"] == lesson_id for r in current["rules"]):
            lesson.status = "promoted"  # recover interrupted promotion
        else:
            save_version(root, target, current)
            current["version"] += 1
            current["rules"].append(
                {
                    "lesson_id": lesson_id,
                    "rule": lesson.proposed_rule,
                    "eval": lesson.eval_proposal,
                    "review_after": lesson.review_after,
                    "at": now(),
                    "actor": "human:local-tty",
                }
            )
            atomic_write(target, yaml_bytes(current))
            lesson.status = "promoted"
        atomic_write(path, yaml_bytes(lesson.model_dump()))
        return current


def save_version(root, target, data):
    path = safe_path(root, f"versions/{target.stem}/{data['version']}.yaml")
    if path.exists():
        require(read_yaml(path) == data, "MEMORY_VERSION_CONFLICT", str(path))
    else:
        atomic_write(path, yaml_bytes(data))


def rollback(project, scope, scenario, version, expected_hash):
    root = safe_path(project, ".content-harness/style-memory")
    with lock(root):
        target = memory_target(root, scope, scenario)
        require(
            digest(target.read_bytes()) == expected_hash, "CONFLICT_EXTERNAL_EDIT", "style memory"
        )
        current = read_yaml(target)
        old = read_yaml(safe_path(root, f"versions/{target.stem}/{version}.yaml"))
        save_version(root, target, current)
        result = {
            "version": current["version"] + 1,
            "rules": old["rules"],
            "rollback_from": version,
            "actor": "human:local-tty",
            "at": now(),
        }
        atomic_write(target, yaml_bytes(result))
        return result
