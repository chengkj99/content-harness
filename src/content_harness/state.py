import os
import uuid
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import Artifact, Event, Manifest
from .storage import (
    HarnessError,
    atomic_write,
    files,
    json_bytes,
    now,
    read_yaml,
    require,
    safe_path,
    tree_hash,
    yaml_bytes,
)
from .workflows import validate


class Run:
    """Caller holds the run lock. Full-state journal is the commit record."""

    def __init__(self, path: Path):
        self.path = path
        journal = safe_path(path, "transitions.jsonl")
        require(journal.exists(), "RUN_NOT_FOUND", str(path))
        raw = journal.read_bytes()
        # Only an unterminated final record can be an interrupted append.
        complete = raw[: raw.rfind(b"\n") + 1]
        require(bool(complete), "JOURNAL_CORRUPT", str(journal))
        events = []
        previous = 0
        for line in complete.splitlines():
            event = Event.model_validate_json(line)
            require(event.state.revision == previous + 1, "JOURNAL_CORRUPT", "revision gap")
            previous = event.state.revision
            events.append(event)
        self.state = events[-1].state
        if complete != raw:
            atomic_write(path / f"journal-tail-{uuid.uuid4().hex}.bin", raw[len(complete) :])
            with journal.open("r+b") as stream:
                stream.truncate(len(complete))
                stream.flush()
                os.fsync(stream.fileno())
        self.workflow = read_yaml(safe_path(path, "workflow.yaml"))
        require(
            tree_hash(files(path / "workflow.yaml")) == self.state.workflow_hash,
            "WORKFLOW_CHANGED",
            "Pinned workflow was modified",
        )
        self.order = validate(self.workflow)
        require(set(self.order) == set(self.state.artifacts), "INVALID_STATE", "artifact IDs")
        for name, record in self.state.artifacts.items():
            require(record.path == self.workflow["artifacts"][name]["path"], "INVALID_STATE", name)
            safe_path(self.path, record.path)
        self.index()

    @classmethod
    def create(cls, path, run_id, workflow, styles, intensity, scenario=None):
        require(not (path / "transitions.jsonl").exists(), "RUN_EXISTS", run_id)
        workflow_path = safe_path(path, "workflow.yaml")
        atomic_write(workflow_path, yaml_bytes(workflow))
        self = cls.__new__(cls)
        self.path, self.workflow, self.order = path, workflow, validate(workflow)
        self.state = Manifest(
            run_id=run_id,
            workflow=workflow["id"],
            scenario=scenario,
            created_at=now(),
            workflow_hash=tree_hash(files(workflow_path)),
            artifacts={
                name: Artifact(path=item["path"]) for name, item in workflow["artifacts"].items()
            },
            style_selection=styles,
            style_intensity=intensity,
        )
        self.save("new")
        return self

    def index(self):
        atomic_write(safe_path(self.path, "manifest.yaml"), yaml_bytes(self.state.model_dump()))
        approvals = b"".join(json_bytes(a.model_dump()) + b"\n" for a in self.state.approvals)
        atomic_write(safe_path(self.path, "approvals.jsonl"), approvals)

    def save(self, command):
        self.state.revision += 1
        event = Event(event_id=uuid.uuid4().hex, at=now(), command=command, state=self.state)
        with safe_path(self.path, "transitions.jsonl").open("ab") as stream:
            stream.write(event.model_dump_json().encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.index()

    def artifact_path(self, name):
        require(name in self.state.artifacts, "ARTIFACT_UNKNOWN", name)
        return safe_path(self.path, self.state.artifacts[name].path)

    def contents(self, name):
        data = files(self.artifact_path(name))
        if name == "visual-assets":
            assets = safe_path(self.path, "artifacts/assets")
            data.update({"assets/" + key: value for key, value in files(assets).items()})
        return data

    def hash(self, name):
        return tree_hash(self.contents(name))

    def snapshot(self, name):
        value = self.hash(name)
        require(value is not None, "ASSET_MISSING", name)
        directory = safe_path(self.path, "snapshots/" + value.split(":")[1])
        for key, content in self.contents(name).items():
            target = safe_path(directory, key)
            if target.exists():
                require(target.read_bytes() == content, "SNAPSHOT_CORRUPT", str(target))
            else:
                atomic_write(target, content)
                target.chmod(0o444)
        return value

    def approved(self, gate):
        name = self.workflow["gates"][gate]
        record = self.state.artifacts[name]
        return record.status == "done" and any(
            a.gate == gate
            and a.content_hash == record.content_hash
            and a.artifact_revision == record.revision
            for a in self.state.approvals
        )

    def blockers(self, name):
        item = self.workflow["artifacts"][name]
        blockers = [
            f"dependency:{dep}"
            for dep in item["depends_on"]
            if self.state.artifacts[dep].status != "done"
        ]
        if item.get("gate") and not self.approved(item["gate"]):
            blockers.append("approval:" + item["gate"])
        return blockers

    def invalidate_descendants(self, roots):
        affected = set(roots)
        for name in self.order:
            deps = self.workflow["artifacts"][name]["depends_on"]
            if affected.intersection(deps):
                affected.add(name)
                record = self.state.artifacts[name]
                if record.status != "missing":
                    record.status, record.reason = "stale", "dependency_changed"
        return affected

    def scan(self):
        before = self.state.model_dump_json()
        changed = set()
        for name in self.order:
            record = self.state.artifacts[name]
            current = self.hash(name)
            if current != record.content_hash:
                record.revision += 1
                record.content_hash = current
                record.status = "in_progress" if current else "missing"
                record.reason = "external_edit_requires_check"
                changed.add(name)
        self.invalidate_descendants(changed)
        for name in self.order:
            record = self.state.artifacts[name]
            if record.status == "done" and (
                self.blockers(name)
                or any(
                    self.state.artifacts[dep].content_hash != value
                    for dep, value in record.depends_on.items()
                )
            ):
                record.status, record.reason = "stale", "dependency_or_approval_changed"
                self.invalidate_descendants({name})
        if before != self.state.model_dump_json():
            self.save("scan")

    def register(self, name):
        from .gates import validate_artifact

        require(not self.blockers(name), "DEPENDENCY_BLOCKED", ", ".join(self.blockers(name)))
        validate_artifact(self, name)
        record = self.state.artifacts[name]
        record.content_hash = self.snapshot(name)
        record.registered_hash = record.content_hash
        record.revision += 1
        record.status, record.reason = "done", None
        record.depends_on = {
            dep: self.state.artifacts[dep].content_hash
            for dep in self.workflow["artifacts"][name]["depends_on"]
        }
        self.save("check:" + name)

    def report(self):
        ready = []
        gates = []
        if "claims" in self.state.artifacts and self.artifact_path("claims").is_file():
            from .gates import claim_batch_hash, claim_verification_items

            try:
                items = claim_verification_items(self, pending_only=True)
            except (HarnessError, ValidationError, yaml.YAMLError, ValueError, OSError):
                items = []
            if items:
                gates.append(
                    {
                        "gate": "claims",
                        "claim_ids": [item["claim_id"] for item in items],
                        "summaries": [item["text"] for item in items],
                        "hash": claim_batch_hash(items),
                        "command": f"content-harness verify-claims {self.state.run_id}",
                    }
                )
        for gate, name in self.workflow["gates"].items():
            if self.state.artifacts[name].status == "done" and not self.approved(gate):
                gates.append(
                    {
                        "gate": gate,
                        "hash": self.state.artifacts[name].content_hash,
                        "command": f"content-harness approve {self.state.run_id} {gate}",
                    }
                )
        for name in self.order:
            if self.state.artifacts[name].status != "done" and not self.blockers(name):
                ready.append({"artifact": name, "skill": self.workflow["artifacts"][name]["skill"]})
        return {
            **self.state.model_dump(),
            "ready": ready,
            "human_gates": gates,
            "next": gates[0] if gates else (ready[0] if ready else None),
            "blocked": {name: self.blockers(name) for name in self.order if self.blockers(name)},
        }
