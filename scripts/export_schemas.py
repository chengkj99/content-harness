"""Generate public JSON Schema from the authoritative Pydantic models."""

import argparse
import json
from pathlib import Path

from content_harness.models import (
    Approval,
    Artifact,
    Claims,
    Event,
    Feedback,
    Manifest,
    Review,
    Sources,
    StyleReport,
    StyleSpec,
    Visuals,
)

MODELS = {
    "manifest": Manifest,
    "artifact": Artifact,
    "event": Event,
    "approval": Approval,
    "claims": Claims,
    "sources": Sources,
    "style-spec": StyleSpec,
    "style-feedback": Feedback,
    "review": Review,
    "style-report": StyleReport,
    "visuals": Visuals,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "schemas"
    root.mkdir(exist_ok=True)
    for name, model in MODELS.items():
        path = root / f"{name}.schema.json"
        content = json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2) + "\n"
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit(f"Schema out of date: {path.name}")
        else:
            path.write_text(content)


if __name__ == "__main__":
    main()
