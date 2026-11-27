"""Audit trail reconstruction for M14 Provenance & Database."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from eclair.database.repositories.audit_repository import AuditRepository
from eclair.exceptions import ModuleError


@dataclass
class DecisionPath:
    """Complete reconstructed audit trail and explanation for a query."""

    query_id: str
    question: str
    final_answer: str | None
    created_at: str | None
    claims: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    verifications: List[Dict[str, Any]] = field(default_factory=list)
    confidence: Dict[str, Any] | None = None
    consensus: Dict[str, Any] | None = None
    risk: Dict[str, Any] | None = None
    decision: Dict[str, Any] | None = None
    feedback: List[Dict[str, Any]] = field(default_factory=list)
    audit_summary: Dict[str, Any] | None = None
    explanation: str = ""
    is_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert decision path to serializable dictionary."""
        return asdict(self)


class AuditReconstructor:
    """Reconstructs the decision path and lineage trail for a query without recomputing signals."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    def reconstruct(self, query_id: str) -> DecisionPath:
        """Reconstruct the entire decision path and lineage for a given query_id.

        Args:
            query_id: Unique query identifier.

        Returns:
            DecisionPath containing complete lineage and structured explanation.

        Raises:
            ModuleError: If query_id is not found in the database.
        """
        if not query_id or not str(query_id).strip():
            raise ModuleError("query_id cannot be empty", code="empty_query_id")

        lineage = self.audit_repo.get_full_lineage(query_id)
        if lineage is None:
            raise ModuleError(
                f"No lineage records found for query_id {query_id!r}",
                code="query_not_found",
            )

        claims = lineage.get("claims", [])
        evidence = lineage.get("evidence", [])
        verifications = lineage.get("verifications", [])
        confidence = lineage.get("confidence")
        consensus = lineage.get("consensus")
        risk = lineage.get("risk")
        decision = lineage.get("decision")
        feedback = lineage.get("feedback", [])
        audit_info = lineage.get("audit")

        # Determine if required lineage elements are all present
        has_decision = decision is not None and "action" in decision
        has_confidence = confidence is not None
        has_risk = risk is not None
        has_verifications = len(verifications) > 0 or len(claims) == 0
        is_complete = bool(has_decision and has_confidence and has_risk and has_verifications)

        explanation = self._build_explanation(
            question=lineage.get("question", ""),
            final_answer=lineage.get("final_answer"),
            claims=claims,
            verifications=verifications,
            confidence=confidence,
            consensus=consensus,
            risk=risk,
            decision=decision,
            is_complete=is_complete,
        )

        audit_summary = audit_info.get("summary") if audit_info else None

        return DecisionPath(
            query_id=query_id,
            question=lineage.get("question", ""),
            final_answer=lineage.get("final_answer"),
            created_at=lineage.get("created_at"),
            claims=claims,
            evidence=evidence,
            verifications=verifications,
            confidence=confidence,
            consensus=consensus,
            risk=risk,
            decision=decision,
            feedback=feedback,
            audit_summary=audit_summary,
            explanation=explanation,
            is_complete=is_complete,
        )

    def _build_explanation(
        self,
        question: str,
        final_answer: str | None,
        claims: List[Dict[str, Any]],
        verifications: List[Dict[str, Any]],
        confidence: Dict[str, Any] | None,
        consensus: Dict[str, Any] | None,
        risk: Dict[str, Any] | None,
        decision: Dict[str, Any] | None,
        is_complete: bool,
    ) -> str:
        """Construct an explainable narrative of the decision path from recorded outputs."""
        parts: list[str] = []

        parts.append(f"Query: '{question}'")

        if claims:
            parts.append(f"Extracted {len(claims)} claim(s).")
            # Tally verification statuses
            supported_count = sum(1 for v in verifications if v.get("status") == "SUPPORTED")
            contradicted_count = sum(1 for v in verifications if v.get("status") == "CONTRADICTED")
            unknown_count = sum(1 for v in verifications if v.get("status") == "UNKNOWN")
            parts.append(
                f"Verification outcomes: {supported_count} SUPPORTED, "
                f"{contradicted_count} CONTRADICTED, {unknown_count} UNKNOWN."
            )
        else:
            parts.append("No atomic claims extracted.")

        if confidence:
            raw = confidence.get("raw_confidence")
            ecs = confidence.get("calibrated_ecs")
            ecs_str = f"{ecs:.4f}" if ecs is not None else "None"
            parts.append(f"Confidence: raw={raw:.4f}, calibrated_ecs={ecs_str}.")

        if consensus:
            parts.append(
                f"Consensus: level={consensus.get('consensus_level')}, "
                f"agreement={consensus.get('agreement_score', 0.0):.4f}."
            )

        if risk:
            parts.append(
                f"Risk: level={risk.get('risk_level')}, "
                f"score={risk.get('risk_score')}."
            )

        if decision:
            parts.append(
                f"Decision action: {decision.get('action')} "
                f"(reason: {decision.get('reason')!r})."
            )
        else:
            parts.append("Decision: Not recorded.")

        if final_answer:
            parts.append(f"Final answer: '{final_answer[:120]}...'")

        if not is_complete:
            parts.append("Note: Audit trail is partial; one or more pipeline stages were not recorded.")

        return " ".join(parts)
