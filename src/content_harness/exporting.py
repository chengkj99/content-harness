from .gates import render_article, validate_artifact
from .profiles import profile
from .storage import atomic_write, files, require, safe_path, tree_hash


def package(run, titles, summary, expected_hash):
    path = run.artifact_path("publish-package")
    require(
        run.hash("publish-package") == (None if expected_hash == "missing" else expected_hash),
        "CONFLICT_EXTERNAL_EDIT",
        "publish-package",
    )
    require(
        not run.blockers("publish-package"),
        "DEPENDENCY_BLOCKED",
        str(run.blockers("publish-package")),
    )
    # Never overwrite existing package content; make changes in a new run or move the old directory.
    require(not path.exists(), "PACKAGE_EXISTS", "Move the old package aside before rebuilding")
    article = render_article(run)
    contents = {
        "article.md": article.encode(),
        "titles.txt": titles.read_bytes(),
        "summary.txt": summary.read_bytes(),
        "sources.yaml": run.artifact_path("sources").read_bytes(),
        "images.yaml": run.artifact_path("visual-assets").read_bytes(),
    }
    contents.update(
        {
            "assets/" + key: value
            for key, value in files(safe_path(run.path, "artifacts/assets")).items()
        }
    )
    for key, data in contents.items():
        atomic_write(safe_path(path, key), data)
    run.scan()
    run.register("publish-package")


def export(run, project, target):
    require(run.approved("publish"), "APPROVAL_REQUIRED", "publish")
    validate_artifact(run, "publish-package")
    config = profile(project)
    require(target in config["exports"], "EXPORT_UNKNOWN", target)
    relative = config["exports"][target]["directory"].format(run_id=run.state.run_id)
    destination = safe_path(project, relative)
    for forbidden in [".git", ".content-harness", "wiki"]:
        require(not destination.is_relative_to(project / forbidden), "EXPORT_FORBIDDEN", relative)
    contents = run.contents("publish-package")
    current_hash = tree_hash(contents)
    key = target + ":" + relative
    if destination.exists():
        require(
            run.state.exports.get(key) == current_hash
            and tree_hash(files(destination)) == current_hash,
            "EXPORT_CONFLICT",
            str(destination),
        )
        return {"path": str(destination), "idempotent": True, "content_hash": current_hash}
    # Intent is durable before file writes; retry accepts only an exact complete copy.
    run.state.exports[key] = current_hash
    run.save("export-intent")
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in contents.items():
        atomic_write(safe_path(destination, name), data)
    require(tree_hash(files(destination)) == current_hash, "EXPORT_INCOMPLETE", str(destination))
    run.save("export-complete")
    return {"path": str(destination), "idempotent": False, "content_hash": current_hash}
