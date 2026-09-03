"""Unit tests for M06 SourceAuthorityScorer and source authority evaluation."""

from __future__ import annotations

from eclair.evidence.authority import (
    SourceAuthorityScorer,
    is_low_quality_source,
    score_source_authority,
)


def test_controlled_kb_policies_receive_maximum_authority() -> None:
    scorer = SourceAuthorityScorer()
    policies = [
        "data/knowledge_base/refund_policy/refund_policy.md",
        "data/knowledge_base/customer_policy.md",
        "kb/company_policy.md",
        "invoice_policy.txt",
        "product_policy.json",
    ]
    for p in policies:
        score = scorer.score(p)
        assert score == 1.0, f"Expected 1.0 for {p}, got {score}"
        assert not scorer.is_low_quality(p)


def test_official_and_regulatory_sources() -> None:
    scorer = SourceAuthorityScorer()
    assert scorer.score("https://ftc.gov/terms") == 0.95
    assert scorer.score("mit.edu/policy.pdf") == 0.95
    assert scorer.score("legal_compliance_standard.md") == 0.95
    assert scorer.score("official_terms.txt") == 0.95


def test_internal_docs_and_handbooks() -> None:
    scorer = SourceAuthorityScorer()
    assert scorer.score("internal/employee_handbook.md") == 0.85
    assert scorer.score("docs/standard_operating_procedure.pdf") == 0.85


def test_general_wiki_and_faq() -> None:
    scorer = SourceAuthorityScorer()
    assert scorer.score("wiki/user_guide.md") == 0.65
    assert scorer.score("faq/billing_questions.html") == 0.65


def test_unverified_blogs_and_social_sources() -> None:
    scorer = SourceAuthorityScorer()
    assert scorer.score("my_personal_blog.com/post/1") == 0.35
    assert scorer.score("reddit.com/r/returns") == 0.35
    assert scorer.score("forum/thread_123") == 0.35
    assert scorer.is_low_quality("my_personal_blog.com/post/1")


def test_missing_empty_none_sources() -> None:
    scorer = SourceAuthorityScorer()
    assert scorer.score(None) == 0.20
    assert scorer.score("") == 0.20
    assert scorer.score("   ") == 0.20
    assert scorer.is_low_quality(None)
    assert scorer.is_low_quality("")


def test_untrusted_and_spam_sources() -> None:
    scorer = SourceAuthorityScorer()
    assert scorer.score("untrusted_fake_phishing_site.com") == 0.10
    assert scorer.is_low_quality("untrusted_fake_phishing_site.com")


def test_custom_authority_mappings() -> None:
    custom = {
        "https://api.partner.com/docs": 0.92,
        "legacy_kb": 0.45,
    }
    scorer = SourceAuthorityScorer(custom_mappings=custom)
    assert scorer.score("https://api.partner.com/docs") == 0.92
    assert scorer.score("legacy_kb/item.txt") == 0.45


def test_metadata_overrides() -> None:
    scorer = SourceAuthorityScorer()
    # Explicit numerical score
    assert scorer.score("unknown_source", metadata={"authority_score": 0.88}) == 0.88
    # Explicit tier string
    assert scorer.score("unknown_source", metadata={"tier": "official"}) == 0.95
    assert scorer.score("unknown_source", metadata={"source_tier": "unverified"}) == 0.35


def test_standalone_convenience_functions() -> None:
    assert score_source_authority("data/knowledge_base/refund_policy.md") == 1.0
    assert is_low_quality_source("unverified_blog.com")
    assert not is_low_quality_source("data/knowledge_base/refund_policy.md")
