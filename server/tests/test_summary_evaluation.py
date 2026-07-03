"""Tests for the deterministic parts of summary evaluation."""

# Import the dataset builder and field checker as the evaluation contract.
from evals.evaluate_summaries import build_listing, field_coverage


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
