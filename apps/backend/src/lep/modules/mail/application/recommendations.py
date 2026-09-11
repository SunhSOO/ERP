"""Project-context recommendation scoring.

Deterministic scoring based on project code/name/customer name, message
intent/milestone, and approved-mail context. No LLM, embeddings, auto-approval,
or database writes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from lep.modules.mail.domain.entities import (
    Classification,
    Confidence,
    MailMessage,
    MailProjectSuggestion,
)
from lep.modules.projects.public import ProjectContextRef


@dataclass(frozen=True, slots=True)
class _ScoredProject:
    project: ProjectContextRef
    score: int
    reasons: tuple[str, ...]


def recommend_projects(
    message: MailMessage,
    projects: Sequence[ProjectContextRef],
    approved_contexts: Sequence[tuple[str, str | None, str | None]] = (),
) -> tuple[MailProjectSuggestion, ...]:
    """Score and rank projects for an unclassified message.

    Args:
        message: Mail message to score against projects.
        projects: List of available projects with code/name/customer.
        approved_contexts: (project_id, intent, milestone_code) from approved mails.

    Returns:
        Up to 3 unambiguous suggestions. Empty when nothing matches or the top
        two tie, because an ambiguous recommendation is worse than none: it
        looks like an answer while carrying no more information than a guess.
    """

    if message.classification != Classification.UNCLASSIFIED:
        return ()

    # Score each project
    scored = [_score(message, project, approved_contexts) for project in projects]

    # Filter to non-zero scores
    ranked = sorted(
        (item for item in scored if item.score > 0),
        key=lambda item: (-item.score, item.project.id),
    )

    # Reject if top candidates are tied
    if len(ranked) > 1 and ranked[0].score == ranked[1].score:
        return ()

    # Return up to 3, convert to suggestions
    return tuple(_to_suggestion(item) for item in ranked[:3])


def _score(
    message: MailMessage,
    project: ProjectContextRef,
    approved_contexts: Sequence[tuple[str, str | None, str | None]],
) -> _ScoredProject:
    """Score a single project against the message."""

    score = 0
    reasons: list[str] = []

    # Case-insensitive text matching
    subject_lower = message.subject.lower()
    body_lower = message.body.lower()
    subject_body = (subject_lower + " " + body_lower)  # Search in both
    code_lower = project.code.lower()
    name_lower = project.name.lower()
    customer_lower = project.customer_name.lower()

    # Extract the meaningful part of the code (after hyphen if present)
    # e.g., "PRJ-DAON" → also match "DAON"
    code_parts = project.code.split("-")
    meaningful_code = code_parts[-1].lower() if code_parts else code_lower

    # Code match (high value) - try both full code and meaningful part
    if code_lower in subject_lower or meaningful_code in subject_lower:
        score += 10
        reasons.append(f"프로젝트 코드: {project.code}")

    # Name match (medium value) - search in both subject and body
    if name_lower in subject_body:
        score += 8
        reasons.append(f"프로젝트명: {project.name}")

    # Customer match (medium value) - search in both subject and body
    if customer_lower in subject_body:
        score += 7
        reasons.append(f"고객사: {project.customer_name}")

    # Approved context match for this project (project-specific signals)
    # Milestone and intent only score when they match this project's approved context
    for approved_id, approved_intent, approved_milestone in approved_contexts:
        if approved_id == project.id:
            # Milestone bonus: only if message milestone matches approved milestone for this project
            if (message.milestone_code and approved_milestone and
                message.milestone_code.lower() == approved_milestone.lower() and
                message.milestone_code.lower() in subject_lower):
                score += 6
                reasons.append(f"마일스톤: {message.milestone_code}")

            # Intent bonus: only if message intent matches approved intent for this project
            if (message.intent and approved_intent and
                message.intent.lower() == approved_intent.lower() and
                message.intent.lower() in subject_body):
                score += 5
                reasons.append(f"의도: {message.intent}")

    return _ScoredProject(project=project, score=score, reasons=tuple(reasons))


def _to_suggestion(scored: _ScoredProject) -> MailProjectSuggestion:
    """Convert scored project to suggestion with confidence level."""

    # Map score to confidence
    if scored.score >= 10:
        confidence = Confidence.HIGH
    elif scored.score >= 6:
        confidence = Confidence.MEDIUM
    else:
        confidence = Confidence.LOW

    return MailProjectSuggestion(
        project_id=scored.project.id,
        project_name=scored.project.name,
        confidence=confidence,
        reasons=scored.reasons,
    )
