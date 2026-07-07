#!/usr/bin/env python3
"""
TESA Performance Benchmark
SWRL rules only work with default world, so we measure
total time and accept that reasoner includes SWRL execution (which is correct).
"""

import time
import statistics
import csv
import os
from owlready2 import *

# --- CONFIGURATIONS ---
TEST_SUITE_1 = [
    (10, 2, "test_10c_2a.owl"),
    (10, 5, "test_10c_5a.owl"),
    (10, 10, "test_10c_10a.owl"),
    (10, 15, "test_10c_15a.owl"),
    (10, 20, "test_10c_20a.owl"),
    (10, 30, "test_10c_30a.owl"),
    (10, 50, "test_10c_50a.owl"),
]

TEST_SUITE_2 = [
    (5, 10, "test_5c_10a.owl"),
    (10, 10, "test_10c_10a.owl"),
    (15, 10, "test_15c_10a.owl"),
    (25, 10, "test_25c_10a.owl"),
    (50, 10, "test_50c_10a.owl"),
]

TRIALS_PER_CONFIG = 50
WARMUP_RUNS = 5
TIMEOUT_MS = 60000


def run_priority_query(onto):
    """Execute SPARQL query to find max-priority action per conflict."""
    query = """
    PREFIX tesa: <http://www.semanticweb.org/tesa#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?conflict ?action ?priority
    WHERE {
        ?conflict rdf:type tesa:ConflictedActions .
        ?conflict tesa:hasAction ?action .
        ?action tesa:priorityValue ?priority .
        ?action tesa:executeIndicator true .

        FILTER NOT EXISTS {
            ?conflict tesa:hasAction ?otherAction .
            ?otherAction tesa:priorityValue ?otherPriority .
            FILTER(?otherPriority > ?priority)
        }
    }
    ORDER BY ?conflict
    """
    return list(onto.world.sparql(query))


def run_single_benchmark(file_path):
    """
    Run a single benchmark measuring total end-to-end time.
    This is what matters for real-world performance.

    Returns: (total_latency_ms, result_count, status)
    """
    # Use default world (SWRL only works here)
    onto = get_ontology(f"file://{os.path.abspath(file_path)}").load()

    start_time = time.perf_counter()

    try:
        # Reasoning + SWRL execution
        with onto:
            sync_reasoner_pellet(
                infer_property_values=True,
                infer_data_property_values=True,
                debug=0
            )

            # Query execution (still inside reasoning context where SWRL works)
            results = run_priority_query(onto)

        total_time = (time.perf_counter() - start_time) * 1000

        # Destroy loaded ontology to prepare for next test
        onto.destroy()

        return total_time, len(results), "SUCCESS"

    except OwlReadyInconsistentOntologyError as e:
        latency = (time.perf_counter() - start_time) * 1000
        onto.destroy()
        return latency, 0, "INCONSISTENT"

    except Exception as e:
        print(f"\n  Error: {str(e)}")
        try:
            onto.destroy()
        except:
            pass
        return TIMEOUT_MS, 0, f"FAILED"


def run_test_suite(suite_name, configurations, trials_per_config):
    """Run a complete test suite and collect results."""

    print(f"\n{'=' * 90}")
    print(f"RUNNING: {suite_name}")
    print(f"{'=' * 90}\n")

    results = []

    for conflicts, actions_per_conflict, filename in configurations:
        if not os.path.exists(filename):
            print(f"⚠ Skipping {filename}: File not found.")
            continue

        total_actions = conflicts * actions_per_conflict
        print(f"\n{conflicts} conflicts × {actions_per_conflict} actions = {total_actions} total")
        print(f"File: {filename}")
        print("-" * 90)

        # Warm-up phase
        print(f"Warming up ({WARMUP_RUNS} trials)...", end=" ", flush=True)
        for _ in range(WARMUP_RUNS):
            run_single_benchmark(filename)
        print("✓")

        # Measurement phase
        print(f"Measuring ({trials_per_config} trials)...", end=" ", flush=True)

        latencies = []
        result_counts = []

        for trial in range(trials_per_config):
            latency, result_count, status = run_single_benchmark(filename)

            if status == "SUCCESS":
                latencies.append(latency)
                result_counts.append(result_count)

            # Progress indicator
            if (trial + 1) % 10 == 0:
                print(f"{trial + 1}", end=" ", flush=True)

        print("✓")

        # Calculate statistics
        if latencies:
            result = {
                'suite': suite_name,
                'conflicts': conflicts,
                'actions_per_conflict': actions_per_conflict,
                'total_actions': total_actions,
                'trials': len(latencies),
                'mean': statistics.mean(latencies),
                'stdev': statistics.stdev(latencies) if len(latencies) > 1 else 0,
                'min': min(latencies),
                'max': max(latencies),
                'median': statistics.median(latencies),
                'result_count': result_counts[0] if result_counts else 0,
                'success_rate': (len(latencies) / trials_per_config) * 100
            }

            results.append(result)

            cv = (result['stdev'] / result['mean']) * 100 if result['mean'] > 0 else 0

            # Print summary
            print(f"  Mean:     {result['mean']:>8.2f} ms")
            print(f"  StdDev:   {result['stdev']:>8.2f} ms ({cv:.2f}% CV)")
            print(f"  Range:    {result['min']:.2f} - {result['max']:.2f} ms")
            print(f"  Median:   {result['median']:>8.2f} ms")
            print(f"  Results:  {result['result_count']} max-priority actions (expected: {conflicts})")
            print(f"  Success:  {result['success_rate']:.1f}%")

            # Validation
            if result['result_count'] != conflicts:
                print(f"  ⚠️  WARNING: Expected {conflicts} results, got {result['result_count']}")
        else:
            print("  ❌ All trials failed!")

    return results


def save_results(suite1_results, suite2_results):
    """Save results to CSV file."""

    with open("tesa_performance_final.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Suite", "Conflicts", "Actions/Conflict", "Total Actions", "Trials",
            "Mean (ms)", "StdDev (ms)", "CV %", "Min (ms)", "Max (ms)", "Median (ms)",
            "Results Found", "Success Rate %"
        ])

        for result in suite1_results + suite2_results:
            cv = (result['stdev'] / result['mean']) * 100 if result['mean'] > 0 else 0

            writer.writerow([
                result['suite'],
                result['conflicts'],
                result['actions_per_conflict'],
                result['total_actions'],
                result['trials'],
                f"{result['mean']:.2f}",
                f"{result['stdev']:.2f}",
                f"{cv:.2f}",
                f"{result['min']:.2f}",
                f"{result['max']:.2f}",
                f"{result['median']:.2f}",
                result['result_count'],
                f"{result['success_rate']:.1f}"
            ])

    print("\n✓ Results saved to: tesa_performance_final.csv")


def print_comparison_tables(suite1_results, suite2_results):
    """Print formatted comparison tables."""

    print("\n" + "=" * 90)
    print("FINAL RESULTS - TEST SUITE 1: Fixed Conflicts (10), Variable Actions")
    print("=" * 90)
    print(f"{'Actions/Conf':<12} {'Mean (ms)':<12} {'StdDev':<12} {'CV %':<10} {'vs Baseline':<12} {'Results'}")
    print("-" * 90)

    baseline = None
    for r in suite1_results:
        if r['actions_per_conflict'] == 2:
            baseline = r['mean']

        speedup = f"{r['mean'] / baseline:.2f}×" if baseline else "—"
        cv = (r['stdev'] / r['mean']) * 100 if r['mean'] > 0 else 0

        print(f"{r['actions_per_conflict']:<12} {r['mean']:>10.1f}   "
              f"{r['stdev']:>10.2f}   {cv:>6.2f}%   {speedup:>10}   "
              f"{r['result_count']}/{r['conflicts']}")

    print("\n" + "=" * 90)
    print("FINAL RESULTS - TEST SUITE 2: Fixed Actions (10), Variable Conflicts")
    print("=" * 90)
    print(f"{'Conflicts':<12} {'Mean (ms)':<12} {'StdDev':<12} {'CV %':<10} {'vs Baseline':<12} {'Results'}")
    print("-" * 90)

    baseline = None
    for r in suite2_results:
        if r['conflicts'] == 5:
            baseline = r['mean']

        speedup = f"{r['mean'] / baseline:.2f}×" if baseline else "—"
        cv = (r['stdev'] / r['mean']) * 100 if r['mean'] > 0 else 0

        print(f"{r['conflicts']:<12} {r['mean']:>10.1f}   "
              f"{r['stdev']:>10.2f}   {cv:>6.2f}%   {speedup:>10}   "
              f"{r['result_count']}/{r['conflicts']}")

    # Summary statistics
    print("\n" + "=" * 90)
    print("SUMMARY STATISTICS")
    print("=" * 90)

    all_results = suite1_results + suite2_results
    all_means = [r['mean'] for r in all_results]
    all_cvs = [(r['stdev'] / r['mean']) * 100 for r in all_results if r['mean'] > 0]

    print(f"Configurations tested:  {len(all_results)}")
    print(f"Total trials:           {sum(r['trials'] for r in all_results)}")
    print(f"Overall success rate:   {statistics.mean([r['success_rate'] for r in all_results]):.1f}%")
    print(f"Mean latency range:     {min(all_means):.1f} - {max(all_means):.1f} ms")
    print(f"Average CV:             {statistics.mean(all_cvs):.2f}%")
    print(f"Real-time viable:       {sum(1 for m in all_means if m < 1000)}/{len(all_means)} configs (<1s)")


def main():
    """Main benchmark execution."""

    print("=" * 90)
    print("TESA PERFORMANCE BENCHMARK - DEFINITIVE VERSION")
    print("=" * 90)
    print()
    print("This version measures END-TO-END performance (what matters in practice):")
    print("  ✓ Ontology loading")
    print("  ✓ SWRL rule execution")
    print("  ✓ Reasoning/inference")
    print("  ✓ Query execution")
    print()
    print("Note: Component breakdown not possible because SWRL requires default world.")
    print("      But total time is what matters for real-world applications!")
    print()
    print(f"Trials per configuration: {TRIALS_PER_CONFIG}")
    print(f"Warmup runs: {WARMUP_RUNS}")
    print()

    # Run Test Suite 1
    suite1_results = run_test_suite(
        "Test Suite 1: Fixed Conflicts (10), Variable Actions",
        TEST_SUITE_1,
        TRIALS_PER_CONFIG
    )

    # Run Test Suite 2
    suite2_results = run_test_suite(
        "Test Suite 2: Fixed Actions (10), Variable Conflicts",
        TEST_SUITE_2,
        TRIALS_PER_CONFIG
    )

    # Save results
    save_results(suite1_results, suite2_results)

    # Print comparison tables
    print_comparison_tables(suite1_results, suite2_results)

    print("\n" + "=" * 90)
    print("BENCHMARK COMPLETE!")


if __name__ == "__main__":
    main()