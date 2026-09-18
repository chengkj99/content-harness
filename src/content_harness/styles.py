import difflib
import json
import re
import uuid

from .models import Feedback, VoiceContract
from .profiles import author_confirmed, author_path, profile, scenario_preset
from .storage import (
    atomic_write,
    digest,
    files,
    identifier,
    json_bytes,
    lock,
    now,
    read_yaml,
    require,
    safe_path,
    tree_hash,
    yaml_bytes,
)
from .workflows import resources


def pack(style_id):
    identifier(style_id)
    root = resources() / "styles" / style_id
    require((root / "rubric.yaml").is_file(), "STYLE_UNKNOWN", style_id)
    return {**read_yaml(root / "rubric.yaml"), "rules": (root / "STYLE.md").read_text()}


def _reference_payload(project, path):
    resolved = safe_path(project, path)
    require(resolved.is_file(), "STYLE_REFERENCE_MISSING", path)
    value = read_yaml(resolved)
    items = value.get("references", []) if isinstance(value, dict) else []
    require(isinstance(items, list) and items, "STYLE_REFERENCE_INVALID", path)
    return {"path": path, "content_hash": digest(resolved.read_bytes()), "references": items}


def voice_source_data(run, project):
    config = profile(project)
    scenario_id = run.state.scenario or run.state.workflow
    memory_root = safe_path(project, ".content-harness/style-memory")
    author = read_yaml(safe_path(memory_root, "author.yaml"))
    scenario = read_yaml(safe_path(memory_root, f"scenarios/{scenario_id}.yaml"))
    references = [
        _reference_payload(project, path) for path in config["style"].get("reference_files", [])
    ]
    return {
        "scenario_id": scenario_id,
        "selected_styles": list(run.state.style_selection),
        "style_packs": [pack(s) for s in dict.fromkeys(run.state.style_selection)],
        "style_intensity": run.state.style_intensity,
        "author_profile": author_path(project).read_text(),
        "author_memory": author,
        "scenario_memory": scenario,
        "scenario_preset": scenario_preset(config, scenario_id),
        "reference_files": references,
    }


def voice_source_hash(run, project):
    return digest(json_bytes(voice_source_data(run, project)))


def compile_voice_contract(run, project):
    require("voice-contract" in run.state.artifacts, "ARTIFACT_UNKNOWN", "voice-contract")
    require(author_confirmed(project), "AUTHOR_CONFIRMATION_REQUIRED", "confirm-author")
    data = voice_source_data(run, project)
    references = []
    for source in data.pop("reference_files"):
        references.extend(source["references"])
    dimensions = []
    guidance = {}
    requires_signature = False
    style_packs = data.pop("style_packs")
    for style in style_packs:
        dimensions.extend(style.get("dimensions", []))
        for dimension in style.get("dimensions", []):
            guidance.setdefault(
                dimension,
                style.get("dimension_guidance", {}).get(
                    dimension, style.get("anchors", {}).get("3", style["rules"])
                ),
            )
        requires_signature = requires_signature or bool(style.get("requires_signature", False))
    for reference in references:
        dimensions.extend(reference.get("dimensions", []))
        for dimension in reference.get("dimensions", []):
            guidance.setdefault(dimension, reference.get("reason", "对照参考样本评估"))
    for scope, memory in (("author", data["author_memory"]), ("scenario", data["scenario_memory"])):
        for index, rule in enumerate(memory.get("rules", []), start=1):
            dimension = f"{scope}-memory:{rule.get('lesson_id', index)}"
            dimensions.append(dimension)
            guidance[dimension] = rule.get("eval") or rule.get("rule", "检查长期风格规则")
    contract = VoiceContract(
        **data,
        source_hash=voice_source_hash(run, project),
        style_packs=style_packs,
        references=references,
        required_dimensions=list(dict.fromkeys(dimensions)),
        dimension_guidance=guidance,
        requires_signature=requires_signature,
    ).model_dump()
    record = run.state.artifacts["voice-contract"]
    require(
        record.content_hash == record.registered_hash or record.content_hash is None,
        "CONFLICT_EXTERNAL_EDIT",
        "voice-contract has unregistered manual edits; preserve them before recompiling",
    )
    atomic_write(safe_path(run.path, "voice-compiled.yaml"), yaml_bytes(contract))
    atomic_write(run.artifact_path("voice-contract"), yaml_bytes(contract))
    run.scan()
    run.register("voice-contract")
    return contract


def scan_voice_contract(run, project):
    if "voice-contract" not in run.state.artifacts:
        return False
    record = run.state.artifacts["voice-contract"]
    if record.status != "done" or not run.artifact_path("voice-contract").is_file():
        return False
    contract = VoiceContract.model_validate(read_yaml(run.artifact_path("voice-contract")))
    if contract.source_hash == voice_source_hash(run, project):
        return False
    record.status, record.reason = "stale", "voice_sources_changed"
    record.revision += 1
    run.invalidate_descendants({"voice-contract"})
    run.save("scan:voice-contract")
    return True


def compile_style(run, project, selection, intensity):
    require(run.approved("brief"), "APPROVAL_REQUIRED", "brief")
    require(author_confirmed(project), "AUTHOR_CONFIRMATION_REQUIRED", "confirm-author")
    require(intensity in {"low", "medium", "high"}, "INVALID_INTENSITY", intensity)
    # Preserve an observed manual edit before evaluating a requested recompile.
    record = run.state.artifacts["style-spec"]
    require(
        record.content_hash == record.registered_hash or record.content_hash is None,
        "CONFLICT_EXTERNAL_EDIT",
        "style-spec has unregistered manual edits; preserve them before recompiling",
    )
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
    voice_hash = None
    if "voice-contract" in run.state.artifacts:
        require(
            run.state.artifacts["voice-contract"].status == "done",
            "DEPENDENCY_BLOCKED",
            "voice-contract",
        )
        contract = VoiceContract.model_validate(read_yaml(run.artifact_path("voice-contract")))
        require(
            list(dict.fromkeys(selection)) == contract.selected_styles
            and intensity == contract.style_intensity,
            "VOICE_STYLE_MISMATCH",
            "Style selection or intensity changed after the voice contract; rerun voice before the Brief",
        )
        author = contract.author_memory
        scenario = contract.scenario_memory
        author_text = contract.author_profile
        scenario_id = contract.scenario_id
        memory = {
            "author": author,
            "scenario": scenario,
            "author_profile": author_text,
            "references": [r.model_dump() for r in contract.references],
        }
        voice_hash = run.hash("voice-contract")
    else:
        memory_root = safe_path(project, ".content-harness/style-memory")
        with lock(memory_root):
            author = read_yaml(safe_path(memory_root, "author.yaml"))
            scenario_id = run.state.scenario or run.state.workflow
            scenario = read_yaml(safe_path(memory_root, f"scenarios/{scenario_id}.yaml"))
            author_text = author_path(project).read_text()
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
            "scenario_id": scenario_id,
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
        "voice_contract_hash": voice_hash,
    }
    run.state.style_selection, run.state.style_intensity = selection, intensity
    atomic_write(safe_path(run.path, "style-compiled.yaml"), yaml_bytes(spec))
    atomic_write(run.artifact_path("style-spec"), yaml_bytes(spec))
    run.scan()
    run.register("style-spec")
    return spec


def feedback(run, project, artifact, scope, reason, before_hash=None):
    require(scope in {"run", "author", "scenario"}, "INVALID_SCOPE", scope)
    require(artifact in {"draft", "manuscript", "publish-package"}, "INVALID_ARTIFACT", artifact)
    before_hash = before_hash or run.state.artifacts[artifact].registered_hash
    require(bool(before_hash), "SNAPSHOT_MISSING", "Register an initial revision first")
    require(bool(re.fullmatch(r"sha256:[0-9a-f]{64}", before_hash)), "INVALID_HASH", before_hash)
    # The selected baseline must have been registered for THIS artifact in THIS run.
    events = safe_path(run.path, "transitions.jsonl").read_text().splitlines()
    require(
        any(
            json.loads(line)["state"]["artifacts"].get(artifact, {}).get("registered_hash")
            == before_hash
            for line in events
        ),
        "BASELINE_NOT_REGISTERED",
        "Choose a registered revision of the requested artifact",
    )
    baseline = safe_path(run.path, "snapshots/" + before_hash.split(":")[1])
    require(baseline.is_dir(), "SNAPSHOT_MISSING", before_hash)
    before_files = files(baseline)
    require(tree_hash(before_files) == before_hash, "SNAPSHOT_CORRUPT", before_hash)
    member = "article.md" if artifact == "publish-package" else "content"
    after_files = run.contents(artifact)
    require(member in before_files and member in after_files, "ASSET_MISSING", member)
    before, after = before_files[member].decode(), after_files[member].decode()
    require(before != after, "NO_STYLE_DIFF", "No text change in the selected member")
    # Freeze the user's exact input BEFORE any rework; feedback never registers or rewrites it.
    after_hash = run.snapshot(artifact)
    require(after_hash == tree_hash(after_files), "CONFLICT_EXTERNAL_EDIT", artifact)
    lesson = Feedback(
        lesson_id="lesson-" + uuid.uuid4().hex[:12],
        run_id=run.state.run_id,
        artifact=artifact,
        scope=scope,
        scenario=run.state.scenario or run.state.workflow,
        reason=reason,
        before_hash=before_hash,
        after_hash=after_hash,
        compared_member=member,
        diff="".join(
            difflib.unified_diff(
                before.splitlines(True),
                after.splitlines(True),
                fromfile=f"baseline/{member}",
                tofile=f"edited/{member}",
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


def note_feedback(run, project, artifact, scope, reason, reference_path=None, reference_excerpt=None):
    require(scope in {"run", "author", "scenario"}, "INVALID_SCOPE", scope)
    require(artifact in {"draft", "manuscript"}, "INVALID_ARTIFACT", artifact)
    current_hash = run.hash(artifact)
    require(bool(current_hash), "ASSET_MISSING", artifact)
    evidence_type = "reference-comparison" if reference_path or reference_excerpt else "rejection"
    lesson = Feedback(
        lesson_id="lesson-" + uuid.uuid4().hex[:12],
        run_id=run.state.run_id,
        artifact=artifact,
        scope=scope,
        scenario=run.state.scenario or run.state.workflow,
        reason=reason,
        before_hash=run.state.artifacts[artifact].registered_hash or current_hash,
        after_hash=current_hash,
        diff="",
        evidence_type=evidence_type,
        reference_path=reference_path,
        reference_excerpt=reference_excerpt,
    )
    root = safe_path(project, ".content-harness/style-memory")
    with lock(root):
        atomic_write(
            safe_path(root, f"candidates/{lesson.lesson_id}.yaml"), yaml_bytes(lesson.model_dump())
        )
    run.save("style-note:" + lesson.lesson_id)
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
    path = version_path(root, target, data["version"])
    if path.exists():
        require(read_yaml(path) == data, "MEMORY_VERSION_CONFLICT", str(path))
    else:
        atomic_write(path, yaml_bytes(data))


def version_path(root, target, version):
    relative = target.relative_to(root).with_suffix("").as_posix()
    return safe_path(root, f"versions/{relative}/{version}.yaml")


def rollback(project, scope, scenario, version, expected_hash):
    root = safe_path(project, ".content-harness/style-memory")
    with lock(root):
        target = memory_target(root, scope, scenario)
        require(
            digest(target.read_bytes()) == expected_hash, "CONFLICT_EXTERNAL_EDIT", "style memory"
        )
        current = read_yaml(target)
        history = version_path(root, target, version)
        # v0.1 stored scenario versions by basename. Never interpret author
        # history as a custom scenario named "author".
        if not history.exists() and scope == "scenario" and scenario != "author":
            history = safe_path(root, f"versions/{target.stem}/{version}.yaml")
        old = read_yaml(history)
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
