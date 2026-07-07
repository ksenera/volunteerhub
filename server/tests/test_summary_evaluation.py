"""Tests for the deterministic parts of summary evaluation."""

import pytest

# Import the dataset builder, field checker, and CI gate as the evaluation contract.
from evals.evaluate_summaries import assert_thresholds, build_listing, field_coverage


# A complete summary should preserve every required source field.
def test_field_coverage_accepts_complete_summary():
    # Build one deterministic source listing used by the evaluator.
    listing = build_listing(0)
    # Include each required field in a natural one-sentence summary.
    summary = (
        f"{listing['title']} with {listing['organization']} is a "
        f"{listing['commitment']} opportunity in {listing['location']}."
    )
    # Every check should pass for a summary grounded in the source listing.
    assert all(field_coverage(listing, summary).values())


# A missing location should be reported as one specific failed field.
def test_field_coverage_identifies_missing_location():
    # Build the same source listing so expected values remain stable.
    listing = build_listing(0)
    # Deliberately omit location while retaining the other required facts.
    summary = (
        f"{listing['title']} with {listing['organization']} is a "
        f"{listing['commitment']} opportunity."
    )
    # Capture the detailed checks instead of reducing them to one score.
    checks = field_coverage(listing, summary)
    # The evaluator should identify location as the only missing source fact.
    assert checks == {
        "title": True,
        "organization": True,
        "commitment": True,
        "location": False,
    }


# CI thresholds should fail loudly when a metric falls below the agreed baseline.
def test_assert_thresholds_rejects_low_field_coverage():
    # Build a deliberately weak metrics report.
    metrics = {
        "generationSuccessRatePercent": 100,
        "requiredFieldCoveragePercent": 75,
    }
    # The threshold helper exits with an actionable failure message.
    with pytest.raises(SystemExit) as failure:
        assert_thresholds(metrics, min_success_rate=100, min_field_coverage=100)
    # The message should name the specific weak metric.
    assert "required field coverage" in str(failure.value)
