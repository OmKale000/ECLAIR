"""Initial M14 schema migration for ECLAIR provenance and database tables.

Revision ID: 001_initial_m14_schema
Revises: None
Create Date: 2026-10-19 23:40:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_m14_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. queries
    op.create_table(
        "queries",
        sa.Column("query_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_queries_query_id", "queries", ["query_id"], unique=False)

    # 2. claims
    op.create_table(
        "claims",
        sa.Column("claim_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=32), nullable=False, server_default="OTHER"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_claims_claim_id", "claims", ["claim_id"], unique=False)
    op.create_index("ix_claims_query_id", "claims", ["query_id"], unique=False)

    # 3. evidence
    op.create_table(
        "evidence",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_evidence_id", "evidence", ["evidence_id"], unique=False)
    op.create_index("ix_evidence_query_id", "evidence", ["query_id"], unique=False)

    # 4. verifications
    op.create_table(
        "verifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "evidence_ids",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_verifications_query_id", "verifications", ["query_id"], unique=False)
    op.create_index("ix_verifications_claim_id", "verifications", ["claim_id"], unique=False)

    # 5. confidences
    op.create_table(
        "confidences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_confidence", sa.Float(), nullable=False),
        sa.Column("calibrated_ecs", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_confidences_query_id", "confidences", ["query_id"], unique=True)

    # 6. consensus_records
    op.create_table(
        "consensus_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agreement_score", sa.Float(), nullable=False),
        sa.Column("consensus_level", sa.String(length=32), nullable=False),
        sa.Column("majority_answer", sa.Text(), nullable=True),
        sa.Column(
            "details",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_consensus_records_query_id", "consensus_records", ["query_id"], unique=True)

    # 7. risks
    op.create_table(
        "risks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risks_query_id", "risks", ["query_id"], unique=True)

    # 8. decisions
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_decisions_query_id", "decisions", ["query_id"], unique=True)

    # 9. feedbacks
    op.create_table(
        "feedbacks",
        sa.Column("feedback_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feedbacks_feedback_id", "feedbacks", ["feedback_id"], unique=False)
    op.create_index("ix_feedbacks_query_id", "feedbacks", ["query_id"], unique=False)

    # 10. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "query_id",
            sa.String(length=64),
            sa.ForeignKey("queries.query_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("decision_action", sa.String(length=32), nullable=True),
        sa.Column(
            "summary",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_audit_id", "audit_logs", ["audit_id"], unique=False)
    op.create_index("ix_audit_logs_query_id", "audit_logs", ["query_id"], unique=True)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("feedbacks")
    op.drop_table("decisions")
    op.drop_table("risks")
    op.drop_table("consensus_records")
    op.drop_table("confidences")
    op.drop_table("verifications")
    op.drop_table("evidence")
    op.drop_table("claims")
    op.drop_table("queries")
