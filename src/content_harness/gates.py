import re
from collections import Counter
from datetime import date
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

import yaml

from .models import (
    Claims,
    Review,
    Sources,
    StyleReport,
    StyleSpec,
    Visuals,
    VoiceContract,
    VoiceReview,
)
from .storage import HarnessError, digest, files, json_bytes, require, safe_path


def payload(path):
    text = path.read_text()
    if text.startswith("---\n"):
        text = text.split("---", 2)[1]
    result = yaml.safe_load(text)
    require(isinstance(result, dict), "SCHEMA_INVALID", str(path))
    return result


def secret_check(contents):
    for name, data in contents.items():
        require(
            not any(part == ".env" or part.startswith(".env.") for part in name.split("/")),
            "SECRET_DETECTED",
            "dotenv file",
        )
        text = data.decode("utf-8", errors="ignore")
        patterns = [
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            r"\b(?:gh[pousr]_|github_pat_|sk-)[A-Za-z0-9_-]{20,}",
            r"(?i)(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_+/=-]{12,}",
        ]
        require(not any(re.search(p, text) for p in patterns), "SECRET_DETECTED", name)


def links(text, base, boundary):
    require(
        not re.search(r"(?i)<\s*(?:script|iframe|object|embed|img)\b", text),
        "UNSAFE_LINK",
        "Use local Markdown images, no embedded active HTML",
    )
    require(
        not re.search(r"!\[[^\]]*\]\(\s*(?:https?:)?//", text),
        "REMOTE_IMAGE",
        "Register a local image asset first",
    )
    require(
        not re.search(r"!?\[[^\]]*\]\[[^\]]*\]|^\s*\[[^\]]+\]:", text, re.MULTILINE),
        "LINK_SYNTAX_UNSUPPORTED",
        "M1 requires inline Markdown links",
    )
    for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", text):
        target = target.strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme:
            require(parsed.scheme in {"https", "http", "mailto"}, "UNSAFE_LINK", target)
            if parsed.scheme != "mailto":
                require(bool(parsed.netloc), "INVALID_LINK", target)
            continue
        require(not parsed.netloc, "UNSAFE_LINK", target)
        if not parsed.path:
            continue
        decoded = unquote(parsed.path)
        require(not decoded.startswith("/"), "UNSAFE_LINK", target)
        path = base / decoded
        require(path.resolve().is_relative_to(boundary.resolve()), "UNSAFE_LINK", target)
        safe_path(boundary, path.relative_to(boundary).as_posix())
        require(path.is_file(), "LINK_MISSING", target)


def claim_ids(text):
    return re.findall(r"<!--\s*claim:([a-z0-9-]+)\s*-->", text)


def ledger(run):
    return Claims.model_validate(payload(run.artifact_path("claims")))


def claim_hash(claim, sources_hash=None):
    return digest(json_bytes({"claim": claim.model_dump(), "sources_hash": sources_hash}))


def claim_verification_items(run, pending_only=False):
    sources_hash = run.hash("sources")
    items = []
    for claim in ledger(run).claims:
        if claim.risk != "high" and claim.type != "experience":
            continue
        content_hash = claim_hash(claim, sources_hash)
        if pending_only and run.state.claim_verifications.get(claim.claim_id) == content_hash:
            continue
        items.append(
            {
                "claim_id": claim.claim_id,
                "text": claim.text,
                "content_hash": content_hash,
            }
        )
    return items


def claim_batch_hash(items):
    return digest(json_bytes({"claims": items}))


def fidelity(run):
    draft = run.artifact_path("draft").read_text()
    manuscript = run.artifact_path("manuscript").read_text()
    patterns = [
        r"\d+(?:[.,:/-]\d+)*(?:%|％|元|万|亿|年|月|日|个|次|天|小时)?",
        r"https?://[^\s)<>]+",
        r"“[^”]+”",
        r'"[^"\n]+"',
        r"可能|部分|在当前样本中|截至|至少|最多|仅在|不代表",
    ]
    for pattern in patterns:
        require(
            Counter(re.findall(pattern, draft)) == Counter(re.findall(pattern, manuscript)),
            "STYLE_FACT_DRIFT",
            "Protected numbers, links, quotes or qualifiers changed",
        )
    require(
        Counter(claim_ids(draft)) == Counter(claim_ids(manuscript)),
        "STYLE_FACT_DRIFT",
        "claim markers changed",
    )
    for claim in ledger(run).claims:
        for term in claim.protected_terms:
            require(draft.count(term) == manuscript.count(term), "STYLE_FACT_DRIFT", term)


def review_pass(review):
    require(
        review.verdict != "fail"
        and review.fidelity == "pass"
        and not any(f.severity == "blocker" for f in review.findings),
        "REVIEW_BLOCKED",
        review.summary,
    )


def required_style_ids(spec):
    return {
        item["id"]
        for layer in ("scene", "polish")
        for item in spec.style_stack.get(layer, [])
    }


def validate_style_report(run, report):
    selected = required_style_ids(StyleSpec.model_validate(payload(run.artifact_path("style-spec"))))
    assessment_ids = [item.style_id for item in report.rule_assessments]
    assessed = set(assessment_ids)
    require(
        len(assessment_ids) == len(assessed),
        "STYLE_RULE_COVERAGE",
        "Each selected style must be assessed exactly once",
    )
    require(selected == assessed, "STYLE_RULE_COVERAGE", f"missing={selected - assessed}")
    for item in report.rule_assessments:
        require(
            bool(item.evidence.strip()),
            "STYLE_RULE_EVIDENCE_MISSING",
            item.style_id,
        )


def validate_voice_review(run, review):
    review_pass(review)
    contract = VoiceContract.model_validate(payload(run.artifact_path("voice-contract")))
    spec = StyleSpec.model_validate(payload(run.artifact_path("style-spec")))
    configured_styles = [
        item
        for layer in ("scene", "polish")
        for item in spec.style_stack.get(layer, [])
    ]
    required = set(contract.required_dimensions)
    for item in configured_styles:
        required.update(item.get("dimensions", []))
    dimensions = [item.dimension for item in review.assessments]
    require(
        len(dimensions) == len(set(dimensions)) and set(dimensions) == required,
        "VOICE_REVIEW_COVERAGE",
        f"missing={required - set(dimensions)}, unknown={set(dimensions) - required}",
    )
    for assessment in review.assessments:
        require(assessment.score >= 3, "VOICE_REVIEW_LOW_SCORE", assessment.dimension)
    require(review.genericity_test.result == "pass", "VOICE_REVIEW_GENERIC", review.genericity_test.reason)
    requires_signature = contract.requires_signature or any(
        bool(item.get("requires_signature", False)) for item in configured_styles
    )
    if requires_signature:
        require(
            bool(review.signature_passage and review.signature_passage.strip()),
            "VOICE_SIGNATURE_MISSING",
            "Personal narrative requires an author-specific passage",
        )


def validate_claims(run):
    sources = Sources.model_validate(payload(run.artifact_path("sources")))
    source_ids = {s.source_id for s in sources.sources}
    claims = ledger(run).claims
    require(len({c.claim_id for c in claims}) == len(claims), "DUPLICATE_ID", "claims")
    for claim in claims:
        require(bool(re.fullmatch(r"[a-z0-9-]+", claim.claim_id)), "INVALID_ID", claim.claim_id)
        require(claim.status != "pending", "CLAIM_UNSUPPORTED", claim.claim_id)
        for source in claim.sources:
            require(source.source_id in source_ids, "SOURCE_MISSING", source.source_id)
            date.fromisoformat(source.checked_at)
        if claim.type in {"factual", "quantitative"}:
            require(
                claim.status == "supported" and any(s.support == "direct" for s in claim.sources),
                "CLAIM_UNSUPPORTED",
                claim.claim_id,
            )
        if claim.type in {"prediction", "observation"}:
            require(bool(claim.boundary), "CLAIM_BOUNDARY_MISSING", claim.claim_id)
        if claim.type == "experience":
            require(bool(claim.provenance), "EXPERIENCE_PROVENANCE_MISSING", claim.claim_id)
        if claim.risk == "high" or claim.type == "experience":
            require(
                run.state.claim_verifications.get(claim.claim_id)
                == claim_hash(claim, run.hash("sources")),
                "CLAIM_HUMAN_REQUIRED",
                claim.claim_id,
            )


def validate_visuals(run, name):
    visuals = Visuals.model_validate(payload(run.artifact_path(name)))
    require(bool(visuals.images) or bool(visuals.no_images_reason), "VISUAL_REASON_MISSING", name)
    require(
        len({i.path for i in visuals.images}) == len(visuals.images), "DUPLICATE_ID", "image paths"
    )
    if name == "visual-assets":
        planned = Visuals.model_validate(payload(run.artifact_path("visual-plan")))
        require(visuals == planned, "VISUAL_PLAN_MISMATCH", "Update plan before assets")
        for entry in visuals.images:
            require(entry.path.startswith("assets/"), "UNSAFE_PATH", entry.path)
            path = safe_path(run.path / "artifacts", entry.path)
            require(path.is_file(), "IMAGE_MISSING", entry.path)
            data = path.read_bytes()
            if path.suffix.lower() == ".svg":
                try:
                    root = ElementTree.fromstring(data)
                except ElementTree.ParseError as exc:
                    raise HarnessError("IMAGE_INVALID", entry.path) from exc
                require(root.tag.split("}")[-1] == "svg", "IMAGE_INVALID", entry.path)
                require(
                    not re.search(
                        rb"(?i)<(?:script|foreignObject)|\bon\w+\s*=|(?:href|url)\s*[=(]", data
                    ),
                    "IMAGE_UNSAFE",
                    entry.path,
                )
            else:
                valid = (
                    (path.suffix.lower() == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
                    or (
                        path.suffix.lower() in {".jpg", ".jpeg"}
                        and data.startswith(b"\xff\xd8\xff")
                    )
                    or (
                        path.suffix.lower() == ".webp"
                        and data[:4] == b"RIFF"
                        and data[8:12] == b"WEBP"
                    )
                )
                require(valid, "IMAGE_INVALID", entry.path)


def validate_artifact(run, name):
    path = run.artifact_path(name)
    require(path.exists(), "ASSET_MISSING", name)
    secret_check(run.contents(name))
    kind = run.workflow["artifacts"][name]["check"]
    if kind == "package":
        return validate_package(run)
    text = path.read_text()
    require(bool(text.strip()), "ASSET_EMPTY", name)
    if path.suffix == ".md":
        links(text, path.parent, run.path / "artifacts")
    if kind == "sources":
        sources = Sources.model_validate(payload(path)).sources
        require(len({s.source_id for s in sources}) == len(sources), "DUPLICATE_ID", "sources")
        for source in sources:
            parsed = urlsplit(source.url)
            require(
                parsed.scheme in {"https", "http"} and bool(parsed.netloc),
                "INVALID_SOURCE_URL",
                source.source_id,
            )
            date.fromisoformat(source.accessed_at)
    elif kind == "claims":
        validate_claims(run)
    elif kind == "brief":
        data = payload(path)
        for field in ["audience", "question", "thesis", "boundaries", "action", "dedupe"]:
            require(bool(data.get(field)), "BRIEF_FIELD_MISSING", field)
    elif kind == "voice-contract":
        VoiceContract.model_validate(payload(path))
        expected = safe_path(run.path, "voice-compiled.yaml")
        require(
            expected.exists() and expected.read_bytes() == path.read_bytes(),
            "VOICE_CONTRACT_CHANGED",
            "Run voice again",
        )
    elif kind == "style":
        StyleSpec.model_validate(payload(path))
        # CLI compilation is pinned in its own snapshot; manual edits require recompile.
        expected = safe_path(run.path, "style-compiled.yaml")
        require(
            expected.exists() and expected.read_bytes() == path.read_bytes(),
            "STYLE_SPEC_CHANGED",
            "Run style again",
        )
    elif kind in {"draft", "manuscript"}:
        known = {c.claim_id for c in ledger(run).claims}
        used = set(claim_ids(text))
        require(used == known, "CLAIM_COVERAGE", f"missing={known - used}, unknown={used - known}")
        if kind == "manuscript":
            fidelity(run)
    elif kind == "style-report":
        report = StyleReport.model_validate(payload(path))
        validate_review_inputs(run, name, report.input_hashes)
        require(report.fidelity == "pass", "STYLE_FACT_DRIFT", report.reason)
        validate_style_report(run, report)
        fidelity(run)
    elif kind == "voice-review":
        review = VoiceReview.model_validate(payload(path))
        validate_review_inputs(run, name, review.input_hashes)
        validate_voice_review(run, review)
        fidelity(run)
    elif kind in {"fact-review", "review"}:
        review = Review.model_validate(payload(path))
        validate_review_inputs(run, name, review.input_hashes)
        review_pass(review)
        fidelity(run)
        if kind == "fact-review":
            claims = ledger(run).claims
            ids = [a.claim_id for a in review.assessments]
            require(
                len(ids) == len(set(ids)) and set(ids) == {c.claim_id for c in claims},
                "REVIEW_COVERAGE",
                "Assess every claim exactly once",
            )
            for claim in claims:
                assessment = next(a for a in review.assessments if a.claim_id == claim.claim_id)
                if claim.type in {"factual", "quantitative"}:
                    require(assessment.support == "direct", "REVIEW_UNSUPPORTED", claim.claim_id)
    elif kind in {"visual-plan", "visual-assets"}:
        validate_visuals(run, name)


def validate_review_inputs(run, name, hashes):
    expected = {
        dep: run.state.artifacts[dep].content_hash
        for dep in run.workflow["artifacts"][name]["depends_on"]
    }
    require(hashes == expected, "REVIEW_INPUT_CHANGED", "Review must bind every current input hash")


def validate_package(run):
    root = run.artifact_path("publish-package")
    contents = files(root)
    required = {"article.md", "titles.txt", "summary.txt", "sources.yaml", "images.yaml"}
    require(required.issubset(contents), "PACKAGE_INCOMPLETE", str(required - set(contents)))
    require(all(contents[key].strip() for key in required), "PACKAGE_INCOMPLETE", "empty file")
    article = contents["article.md"].decode()
    expected = render_article(run)
    require(
        article == expected, "PACKAGE_CONTENT_CHANGED", "article must match reviewed manuscript"
    )
    require(
        contents["sources.yaml"] == run.artifact_path("sources").read_bytes(),
        "PACKAGE_CONTENT_CHANGED",
        "sources",
    )
    require(
        contents["images.yaml"] == run.artifact_path("visual-assets").read_bytes(),
        "PACKAGE_CONTENT_CHANGED",
        "images",
    )
    for key, data in files(safe_path(run.path, "artifacts/assets")).items():
        require(contents.get("assets/" + key) == data, "PACKAGE_CONTENT_CHANGED", key)
    links(article, root, root)
    secret_check(contents)


def render_article(run):
    """Render reviewed prose plus planned images without a post-review rewrite."""
    manuscript = run.artifact_path("manuscript").read_text()
    article = re.sub(r"<!--\s*claim:[a-z0-9-]+\s*-->", "", manuscript)
    visuals = Visuals.model_validate(payload(run.artifact_path("visual-assets")))
    for entry in visuals.images:
        require(not any(c in entry.alt for c in "[]\n\r"), "IMAGE_ALT_INVALID", entry.path)
        marker = f"![{entry.alt}]({entry.path})"
        if marker in article:
            continue
        if entry.location in {"end", "文章末尾"}:
            article = article.rstrip() + "\n\n" + marker + "\n"
        else:
            anchor = entry.location + "\n"
            require(article.count(anchor) == 1, "VISUAL_LOCATION_INVALID", entry.location)
            article = article.replace(anchor, anchor + "\n" + marker + "\n", 1)
    return article
