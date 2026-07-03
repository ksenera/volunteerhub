"""Measure a VolunteerHub GET endpoint with concurrent HTTP requests."""

# argparse turns command-line flags into Python values.
import argparse
# json prints results in a format CI and future dashboards can read.
import json
# math supplies ceiling for a nearest-rank percentile calculation.
import math
# ThreadPoolExecutor creates a controlled number of concurrent clients.
from concurrent.futures import ThreadPoolExecutor
# perf_counter is a high-resolution monotonic timer for latency measurements.
from time import perf_counter
# HTTPError lets failed HTTP responses become measured errors instead of crashes.
from urllib.error import HTTPError, URLError
# urlopen performs the request without adding another project dependency.
from urllib.request import urlopen


# This helper converts a list of durations into a reproducible percentile.
def percentile(values, percentage):
    # A percentile has no meaning when no requests completed.
    if not values:
        return 0.0
    # Sorting places the fastest request first and slowest request last.
    ordered = sorted(values)
    # Nearest-rank chooses the first item at or above the requested percentage.
    rank = max(1, math.ceil((percentage / 100) * len(ordered)))
    # Python lists start at zero, so rank one is stored at index zero.
    return ordered[rank - 1]


# This helper executes one request and returns both latency and HTTP status.
def request_once(url, timeout):
    # Start timing immediately before opening the HTTP connection.
    started_at = perf_counter()
    try:
        # The context manager closes the response even if reading fails.
        with urlopen(url, timeout=timeout) as response:
            # Reading the body ensures the complete response is measured.
            response.read()
            # Successful responses expose their numeric HTTP status.
            status = response.status
    except HTTPError as error:
        # HTTP errors such as 404 and 500 still contain a useful status code.
        status = error.code
    except URLError:
        # Network failures use zero because no HTTP response was received.
        status = 0
    # Convert elapsed seconds to milliseconds for readable API metrics.
    latency_ms = (perf_counter() - started_at) * 1000
    # Return a plain tuple so concurrent workers stay simple.
    return latency_ms, status


# This function coordinates all clients and produces the final metric record.
def run_benchmark(url, request_count=100, concurrency=10, timeout=5.0):
    # Record total wall-clock time separately from each request latency.
    benchmark_started_at = perf_counter()
    # A thread pool models several users making requests at the same time.
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Submit exactly request_count identical GET requests.
        futures = [executor.submit(request_once, url, timeout) for _ in range(request_count)]
        # Resolve every future so all requests finish before statistics are calculated.
        results = [future.result() for future in futures]
    # Total elapsed time is needed to calculate requests per second.
    elapsed_seconds = perf_counter() - benchmark_started_at
    # Keep every latency, including failed requests, visible in performance results.
    latencies = [latency for latency, _status in results]
    # Count only 2xx responses as successful application requests.
    success_count = sum(1 for _latency, status in results if 200 <= status < 300)
    # Every non-2xx response contributes to the error rate.
    error_count = request_count - success_count
    # Return raw settings and derived measurements together for reproducibility.
    return {
        "url": url,
        "requests": request_count,
        "concurrency": concurrency,
        "successes": success_count,
        "errors": error_count,
        "errorRatePercent": round((error_count / request_count) * 100, 2),
        "requestsPerSecond": round(request_count / elapsed_seconds, 2),
        "averageLatencyMs": round(sum(latencies) / len(latencies), 2),
        "p50LatencyMs": round(percentile(latencies, 50), 2),
        "p95LatencyMs": round(percentile(latencies, 95), 2),
        "p99LatencyMs": round(percentile(latencies, 99), 2),
    }


# This function defines the command-line interface used by developers and CI.
def main():
    # The parser also generates helpful --help output automatically.
    parser = argparse.ArgumentParser(description=__doc__)
    # The default endpoint measures the primary listing-read workflow.
    parser.add_argument("--url", default="http://127.0.0.1:5000/api/listings")
    # Request count controls the sample size of the benchmark.
    parser.add_argument("--requests", type=int, default=100)
    # Concurrency controls how many requests can run simultaneously.
    parser.add_argument("--concurrency", type=int, default=10)
    # Timeout prevents an unavailable server from hanging the benchmark forever.
    parser.add_argument("--timeout", type=float, default=5.0)
    # Parse the values supplied by the person running the script.
    arguments = parser.parse_args()
    # Run the benchmark using the selected endpoint and load settings.
    metrics = run_benchmark(
        arguments.url,
        request_count=arguments.requests,
        concurrency=arguments.concurrency,
        timeout=arguments.timeout,
    )
    # Pretty JSON is readable in a terminal and easy to save as an artifact.
    print(json.dumps(metrics, indent=2))


# This guard prevents command-line parsing when tests import the module.
if __name__ == "__main__":
    # Execute the CLI only when this file is run directly.
    main()
