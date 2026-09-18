from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Artifact(Strict):
    path: str
    status: Literal["missing", "in_progress", "done", "blocked", "stale"] = "missing"
    revision: int = 0
    content_hash: str | None = None
    registered_hash: str | None = None
    depends_on: dict[str, str] = Field(default_factory=dict)
    reason: str | None = None


class Approval(Strict):
    approval_id: str
    at: str
    gate: str
    artifact: str
    content_hash: str
    artifact_revision: int
    actor: Literal["human:local-tty"] = "human:local-tty"
    decision: Literal["approved"] = "approved"


class Manifest(Strict):
    schema_version: Literal[1] = 1
    run_id: str
    workflow: str
    scenario: str | None = None
    created_at: str
    revision: int = 0
    workflow_hash: str
    artifacts: dict[str, Artifact]
    approvals: list[Approval] = Field(default_factory=list)
    style_selection: list[str] = Field(default_factory=list)
    style_intensity: Literal["low", "medium", "high"] = "medium"
    claim_verifications: dict[str, str] = Field(default_factory=dict)
    exports: dict[str, str] = Field(default_factory=dict)
    archived: bool = False


class Event(Strict):
    schema_version: Literal[1] = 1
    event_id: str
    at: str
    command: str
    state: Manifest


class Source(Strict):
    source_id: str
    title: str = Field(min_length=1)
    url: str
    accessed_at: str
    excerpt: str = Field(min_length=1)


class Sources(Strict):
    schema_version: Literal[1] = 1
    sources: list[Source]


class Support(Strict):
    source_id: str
    locator: str = Field(min_length=1)
    support: Literal["direct", "partial", "contextual", "none"]
    checked_at: str


class Claim(Strict):
    claim_id: str
    text: str = Field(min_length=1)
    type: Literal["experience", "observation", "factual", "quantitative", "prediction"]
    risk: Literal["low", "medium", "high"]
    sources: list[Support] = Field(default_factory=list)
    status: Literal["supported", "pending", "author-confirmed", "bounded"]
    provenance: str | None = None
    boundary: str | None = None
    protected_terms: list[str] = Field(default_factory=list)
    narrative_role: Literal["scene", "conflict", "turn", "reflection", "context"] | None = None
    sensitivity: Literal["normal", "private", "sensitive"] = "normal"


class Claims(Strict):
    schema_version: Literal[1] = 1
    claims: list[Claim]


class Finding(Strict):
    location: str
    reason: str
    fix: str
    severity: Literal["warning", "blocker"]


class Assessment(Strict):
    claim_id: str
    support: Literal["direct", "partial", "contextual", "none", "not-applicable"]
    reason: str = Field(min_length=1)


class Review(Strict):
    schema_version: Literal[1] = 1
    input_hashes: dict[str, str]
    verdict: Literal["pass", "warn", "fail"]
    summary: str = Field(min_length=1)
    findings: list[Finding]
    assessments: list[Assessment] = Field(default_factory=list)
    fidelity: Literal["pass", "fail"]


class StyleSpec(Strict):
    schema_version: Literal[1] = 1
    base: dict
    style_stack: dict
    memory_snapshot: dict
    intensity: Literal["low", "medium", "high"]
    apply_to: dict
    protected: list[str]
    voice_contract_hash: str | None = None


class StyleReference(Strict):
    reference_id: str
    role: Literal["positive", "negative"]
    source: str = Field(min_length=1)
    dimensions: list[str] = Field(default_factory=list)
    excerpt: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class VoiceContract(Strict):
    schema_version: Literal[1] = 1
    scenario_id: str
    source_hash: str
    selected_styles: list[str] = Field(default_factory=list)
    style_intensity: Literal["low", "medium", "high"] = "medium"
    author_profile: str = Field(min_length=1)
    author_memory: dict
    scenario_memory: dict
    scenario_preset: dict
    style_packs: list[dict] = Field(default_factory=list)
    references: list[StyleReference] = Field(default_factory=list)
    required_dimensions: list[str] = Field(default_factory=list)
    dimension_guidance: dict[str, str] = Field(default_factory=dict)
    requires_signature: bool = False


class StyleRuleAssessment(Strict):
    style_id: str = Field(min_length=1)
    status: Literal["applied", "already-satisfied", "rejected"]
    evidence: str = Field(min_length=1)


class StyleReport(Strict):
    schema_version: Literal[1] = 1
    input_hashes: dict[str, str]
    changes: list[dict]
    rejected: list[str]
    fidelity: Literal["pass", "fail"]
    reason: str = Field(min_length=1)
    rule_assessments: list[StyleRuleAssessment] = Field(default_factory=list)


class VoiceAssessment(Strict):
    dimension: str = Field(min_length=1)
    score: int = Field(ge=1, le=5)
    location: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    fix: str | None = None


class GenericityTest(Strict):
    result: Literal["pass", "fail"]
    reason: str = Field(min_length=1)


class VoiceReview(Strict):
    schema_version: Literal[1] = 1
    input_hashes: dict[str, str]
    verdict: Literal["pass", "warn", "fail"]
    summary: str = Field(min_length=1)
    fidelity: Literal["pass", "fail"]
    assessments: list[VoiceAssessment]
    signature_passage: str | None = None
    genericity_test: GenericityTest
    findings: list[Finding] = Field(default_factory=list)


class Visual(Strict):
    path: str
    alt: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    source: str = Field(min_length=1)
    license: str = Field(min_length=1)
    location: str = Field(min_length=1)


class Visuals(Strict):
    schema_version: Literal[1] = 1
    images: list[Visual]
    no_images_reason: str | None = None


class Feedback(Strict):
    schema_version: Literal[1] = 1
    lesson_id: str
    run_id: str
    artifact: str
    scope: Literal["run", "author", "scenario"]
    scenario: str
    reason: str
    before_hash: str
    after_hash: str
    diff: str
    compared_member: str | None = None
    evidence_type: Literal["diff", "rejection", "reference-comparison"] = "diff"
    reference_path: str | None = None
    reference_excerpt: str | None = None
    proposed_rule: str = ""
    eval_proposal: str = ""
    review_after: str | None = None
    status: Literal["candidate", "promoted"] = "candidate"
