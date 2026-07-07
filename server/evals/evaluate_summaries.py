"""Evaluate listing summaries for reliability, field coverage, and latency."""

# argparse provides a small command-line interface without another dependency.
import argparse
# json makes evaluation output easy to inspect, compare, and archive.
import json
# os reads the active summary provider from the same environment as the app.
import os
# perf_counter records generation latency with a monotonic high-resolution timer.
from time import perf_counter

# Import the production prompt version so reports cannot drift from the app.
from backend import SUMMARY_PROMPT_VERSION, summarize_listing
# Reuse the tested percentile calculation from the benchmark feature.
from benchmarks.benchmark_api import percentile


# These values create varied but deterministic evaluation records.
TITLES = ["Food Bank Helper", "Library Tutor", "Park Cleanup Lead", "Event Greeter"]
# These organizations pair with the titles while keeping the dataset readable.
ORGANIZATIONS = ["Ottawa Food Bank", "City Library", "Green Ottawa", "Community Arts"]
# These commitments exercise every points and summary wording category.
COMMITMENTS = ["Flexible", "Short term", "Long term", "Ongoing"]
# These locations exercise both remote and in-person summary content.
LOCATIONS = ["Ottawa", "Remote", "Hamilton", "Toronto"]


# This helper creates one stable listing from an integer sample index.
def build_listing(index):
    # Modulo cycles through each small vocabulary without random test results.
    position = index % len(TITLES)
    # The production summarizer only needs these four listing fields.
    return {
        "title": f"{TITLES[position]} {index + 1}",
        "organization": ORGANIZATIONS[position],
        "commitment": COMMITMENTS[position],
        "location": LOCATIONS[position],
    }


# This helper checks whether important source facts survive summarization.
def field_coverage(listing, summary):
    # Case-insensitive comparisons avoid treating capitalization as an AI error.
    normalized_summary = summary.lower()
    # Location includes its expected preposition to avoid matching an organization name.
    location_phrase = f"in {listing['location']}".lower()
    # Each boolean represents one required source field preserved in the output.
    checks = {
        "title": listing["title"].lower() in normalized_summary,
        "organization": listing["organization"].lower() in normalized_summary,
        "commitment": listing["commitment"].lower() in normalized_summary,
        "location": location_phrase in normalized_summary,
    }
    # Return individual checks so failures remain diagnosable.
    return checks


# This function runs the same evaluation contract over a chosen sample size.
def evaluate_summaries(sample_count=50):
    # Latencies are collected separately to calculate average and p95 values.
    latencies = []
    # Successful generations exclude provider exceptions and empty outputs.
    successful_generations = 0
    # Passed field checks count preserved facts across every generated summary.
    passed_field_checks = 0
    # Four required fields are checked for every requested sample.
    total_field_checks = sample_count * 4
    # Process samples sequentially so provider rate limits do not distort results.
    for index in range(sample_count):
        # Build the exact source record used for this evaluation case.
        listing = build_listing(index)
        # Start timing immediately before the production summarizer is called.
        started_at = perf_counter()
        try:
            # Calling production code keeps the evaluation tied to real behaviour.
            summary = summarize_listing(listing)
        except Exception:
            # Provider failures count against success rate without ending the run.
            summary = ""
        # Record milliseconds for both successful and failed provider calls.
        latencies.append((perf_counter() - started_at) * 1000)
        # Empty text is considered an unsuccessful generation.
        if not summary:
            # Continue because there are no fields to evaluate in an empty output.
            continue
        # Count the provider call as successful once non-empty text exists.
        successful_generations += 1
        # Evaluate whether each required listing fact appears in the summary.
        checks = field_coverage(listing, summary)
        # True behaves like one and False like zero when summed in Python.
        passed_field_checks += sum(checks.values())
    # Avoid division by zero if a caller explicitly requests zero samples.
    success_rate = (successful_generations / sample_count * 100) if sample_count else 0
    # Avoid division by zero while preserving a meaningful empty-run result.
    coverage_rate = (passed_field_checks / total_field_checks * 100) if total_field_checks else 0
    # Average latency summarizes overall provider speed across the run.
    average_latency = (sum(latencies) / len(latencies)) if latencies else 0
    # Return version and provider metadata beside every measured value.
    return {
        "provider": os.getenv("AI_PROVIDER", "mock").lower(),
        "promptVersion": SUMMARY_PROMPT_VERSION,
        "samples": sample_count,
        "generationSuccessRatePercent": round(success_rate, 2),
        "requiredFieldCoveragePercent": round(coverage_rate, 2),
        "averageLatencyMs": round(average_latency, 2),
        "p95LatencyMs": round(percentile(latencies, 95), 2),
    }


# This helper enforces quality gates for CI and local checks.
def assert_thresholds(metrics, min_success_rate, min_field_coverage):
    # Collect every failing metric so the terminal output is actionable.
    failures = []
    # Generation success protects against empty or provider-failed outputs.
    if metrics["generationSuccessRatePercent"] < min_success_rate:
        failures.append(
            "generation success "
            f"{metrics['generationSuccessRatePercent']}% is below {min_success_rate}%"
        )
    # Field coverage protects against summaries dropping important listing facts.
    if metrics["requiredFieldCoveragePercent"] < min_field_coverage:
        failures.append(
            "required field coverage "
            f"{metrics['requiredFieldCoveragePercent']}% is below {min_field_coverage}%"
        )
    # Raise one concise error if any gate fails.
    if failures:
        raise SystemExit("; ".join(failures))


# This function defines how a developer runs the evaluation from a terminal.
def main():
    # The module description becomes the command's help text.
    parser = argparse.ArgumentParser(description=__doc__)
    # Fifty samples provide a useful baseline without expensive default API calls.
    parser.add_argument("--samples", type=int, default=50)
    # CI can set a minimum acceptable generation success rate.
    parser.add_argument("--min-success-rate", type=float, default=0)
    # CI can set a minimum acceptable field grounding score.
    parser.add_argument("--min-field-coverage", type=float, default=0)
    # Parse flags supplied after the module name.
    arguments = parser.parse_args()
    # Evaluate the configured provider using the requested sample count.
    metrics = evaluate_summaries(arguments.samples)
    # Fail fast when a caller provided thresholds and the provider misses them.
    assert_thresholds(
        metrics,
        arguments.min_success_rate,
        arguments.min_field_coverage,
    )
    # Print stable JSON so future prompt versions can be compared directly.
    print(json.dumps(metrics, indent=2))


# This guard prevents terminal argument parsing during imports and tests.
if __name__ == "__main__":
    # Run the command-line evaluation only when invoked directly.
    main()
