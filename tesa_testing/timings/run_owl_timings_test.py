#!/usr/bin/env python3
"""
Performance Benchmark: OWL+SWRL Conflict Detection and Auto-Resolution.
Measures the computational cost of resolving inconsistencies in an OWL ontology
triggered by SWRL rule inferences.
"""

import time
import statistics
import csv
import os
from owlready2 import *

# --- CONFIGURATION ---
CONFLICT_COUNTS = [5, 10, 20, 30, 40, 50]
TRIALS_PER_CONFIG = 10
WARMUP_RUNS = 1


def expensive_ontology_repair(onto):
    """
    Simplified MUPS (Minimally Unsatisfiable Preserving Subsets) resolution.
    Iteratively removes conflicting individuals until the Pellet reasoner
    confirms the ontology is consistent.
    """
    repair_start = time.perf_counter()
    iterations = 0
    entities_removed = 0
    max_iterations = 200

    while iterations < max_iterations:
        iterations += 1
        try:
            with onto:
                sync_reasoner_pellet(
                    infer_property_values=True,
                    infer_data_property_values=True,
                    debug=0
                )
            # Success: Ontology is now consistent
            repair_time = (time.perf_counter() - repair_start) * 1000
            return repair_time, iterations, entities_removed, True

        except OwlReadyInconsistentOntologyError:
            # Conflict remains: remove the most recently added individual
            try:

                individuals = list(onto.individuals())

                if not individuals:
                    repair_time = (time.perf_counter() - repair_start) * 1000
                    return repair_time, iterations, entities_removed, False
                states = list(filter(lambda x: x.priorityValue[0] if x.priorityValue else False, individuals))
                states.sort(key=lambda x: x.priorityValue[0] if x.priorityValue else 0)
                state_to_remove = states[0]

                destroy_entity(state_to_remove)
                entities_removed += 1
            except Exception:
                repair_time = (time.perf_counter() - repair_start) * 1000
                return repair_time, iterations, entities_removed, False

    return (time.perf_counter() - repair_start) * 1000, iterations, entities_removed, False


def run_owl_swrl_benchmark(file_path):
    """
    Executes a single benchmark run for an OWL/SWRL file.
    Tracks initial reasoning time vs. repair time.
    """

    # 2. Configure path and IRI
    logical_iri = "http://www.semanticweb.org/owl_swrl_comparison#"
    abs_dir = os.path.dirname(os.path.abspath(file_path))

    # 3. Add local directory to search path
    if abs_dir not in onto_path:
        onto_path.append(abs_dir)

    # 3. Load using logical IRI
    onto = get_ontology(os.path.abspath(file_path)).load()
    inds = list(onto.individuals())
    if not inds:
        print(f"  ⚠️ Warning: No individuals found in {file_path}")
    all_inds = list(default_world.individuals())
    print(onto.base_iri)
    print(onto.name)
    overall_start = time.perf_counter()

    try:
        reasoning_start = time.perf_counter()
        with onto:
            sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True)

        reasoning_time = (time.perf_counter() - reasoning_start) * 1000
        total_time = (time.perf_counter() - overall_start) * 1000
        onto.destroy()
        return total_time, reasoning_time, 0, 0, 0, "NO_CONFLICT"

    except OwlReadyInconsistentOntologyError:
        reasoning_time = (time.perf_counter() - reasoning_start) * 1000
        repair_time, iterations, entities_removed, success = expensive_ontology_repair(onto)
        total_time = (time.perf_counter() - overall_start) * 1000
        onto.destroy()

        status = "REPAIRED" if success else "REPAIR_FAILED"
        return total_time, reasoning_time, repair_time, iterations, entities_removed, status

    except Exception as e:
        total_time = (time.perf_counter() - overall_start) * 1000
        try:
            onto.destroy()
        except:
            pass
        return total_time, 0, 0, 0, 0, f"ERROR"


def save_results(results):
    """Saves OWL performance metrics to CSV."""
    with open("owl_swrl_performance_results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Conflicts", "Total Time (ms)", "StdDev",
            "Initial Reasoning (ms)", "Repair Time (ms)",
            "Iterations", "Entities Removed", "Success Rate %"
        ])

        for res in results:
            o = res['metrics']
            writer.writerow([
                res['conflicts'], f"{o['total_mean']:.2f}", f"{o['total_stdev']:.2f}",
                f"{o['reasoning_mean']:.2f}", f"{o['repair_mean']:.2f}",
                f"{o['iterations_mean']:.1f}", f"{o['entities_removed_mean']:.1f}",
                f"{o['success_rate']:.1f}"
            ])
    print("\n✓ Results saved to: v2_owl_swrl_performance_results.csv")


def main():
    final_results = []
    print("--- OWL+SWRL REPAIR BENCHMARK ---")

    for conflicts in CONFLICT_COUNTS:
        owl_file = f"v2_owl_swrl_{conflicts}c.owl"
        if not os.path.exists(owl_file): continue

        print(f"Testing {conflicts} conflicts...", end=" ", flush=True)

        # Warmup
        for _ in range(WARMUP_RUNS): run_owl_swrl_benchmark(owl_file)

        # Measurement
        metrics = {'total': [], 'reasoning': [], 'repair': [], 'iters': [], 'entities': []}
        for _ in range(TRIALS_PER_CONFIG):
            t, reas, rep, iters, ent, status = run_owl_swrl_benchmark(owl_file)
            if status == "REPAIRED":
                metrics['total'].append(t)
                metrics['reasoning'].append(reas)
                metrics['repair'].append(rep)
                metrics['iters'].append(iters)
                metrics['entities'].append(ent)

        if metrics['total']:
            stats = {
                'total_mean': statistics.mean(metrics['total']),
                'total_stdev': statistics.stdev(metrics['total']) if len(metrics['total']) > 1 else 0,
                'reasoning_mean': statistics.mean(metrics['reasoning']),
                'repair_mean': statistics.mean(metrics['repair']),
                'iterations_mean': statistics.mean(metrics['iters']),
                'entities_removed_mean': statistics.mean(metrics['entities']),
                'success_rate': (len(metrics['total']) / TRIALS_PER_CONFIG) * 100
            }
            final_results.append({'conflicts': conflicts, 'metrics': stats})
            print("Done.")

    save_results(final_results)


if __name__ == "__main__":
    main()