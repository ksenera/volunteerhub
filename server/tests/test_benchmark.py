"""Unit tests for the dependency-free benchmark calculations."""

# Import the exact helper whose boundary behaviour controls reported percentiles.
from benchmarks.benchmark_api import percentile


# This test documents expected nearest-rank results for a small known sample.
def test_percentile_uses_nearest_rank():
    # Deliberately unsorted input verifies that the helper sorts its own data.
    values = [50.0, 10.0, 40.0, 20.0, 30.0]
    # The middle value of five ordered samples is 30.
    assert percentile(values, 50) == 30.0
    # The 95th percentile rounds up to the fifth and slowest sample.
    assert percentile(values, 95) == 50.0


# Empty input should be safe for callers handling a failed benchmark run.
def test_percentile_handles_empty_input():
    # Returning zero avoids a division or indexing exception in report code.
    assert percentile([], 95) == 0.0
