import os

from code.models.ILPhard import run_ilp_hard
from code.models.ILPsoft import run_ilp_soft
from code.models.ILP import run_ilp

from code.models.CPsoft import run_cp_soft
from code.models.CPhard import run_cp_hard
from code.models.CP import run_cp


from code.models.baseline_random import run_random_baseline
from code.evaluation.evaluate_results import run_evaluate
from code.models.baseline_random import run_random_baseline

import sys

def save_results(results, timestamp):
    folder = 'data/results'
    results_folder = os.path.join(folder, school, method)

    solution_folder = os.path.join(results_folder, "solutions")
    print(f"Saving results to {solution_folder}")
    os.makedirs(solution_folder, exist_ok=True)

    output_file = os.path.join(solution_folder, f"{method}_{timestamp}.csv")
    results.to_csv(output_file, index=False)

def run_pipeline():
    print("Running pipeline for school: {}".format(school))

    results = None
    timestamp = None

    # Run random grouping algorithm
    # TODO: not only fix model but also folder struxture
    if run_baseline_heuristic:
        run_random_baseline(school, processed_data_folder)
        # run_greedy(school, processed_data_folder, min_prefs_per_kid, deviation)

    # Run ILP algorithm
    if run_baseline_ilp:
        results, timestamp = run_ilp(school, processed_data_folder, timelimit, min_prefs_per_kid, deviation)

    # Run ILP soft algorithm
    if run_soft_ilp_model:
        results, timestamp = run_ilp_soft(school, processed_data_folder, timelimit)

    # Run ILP hard algorithm
    if run_hard_ilp_model:
        results, timestamp = run_ilp_hard(school, processed_data_folder, timelimit, min_prefs_per_kid, deviation)



    # Run CP algorithm
    if run_cp_model:
        results, timestamp = run_cp(school, processed_data_folder, timelimit, min_prefs_per_kid, deviation)

    # Run CP soft algorithm
    if run_soft_cp_model:
        results, timestamp = run_cp_soft(school, processed_data_folder, timelimit)

    # Run CP hard algorithm
    if run_hard_cp_model:
        results, timestamp = run_cp_hard(school, processed_data_folder, timelimit, min_prefs_per_kid, deviation)

    if results is not None:
        # Save results
        save_results(results, timestamp)
        # Evaluate results
        run_evaluate(school, processed_data_folder, method, results, timestamp)




if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 main.py <school> <method: cp|ilp|greedy|cpsoft|ilpsoft|cphard|ilphard> [timelimit] [min_prefs_per_kid] [deviation]")
        sys.exit(1)

    school = sys.argv[1]
    method = sys.argv[2].upper()
    random_seed = 42

    # Set which model to run
    run_baseline_heuristic = method == "HEURISTIC"
    run_baseline_ilp = method == "ILP"
    run_cp_model = method == "CP"
    run_soft_cp_model = method == "CPSOFT"
    run_soft_ilp_model = method == "ILPSOFT"
    run_hard_cp_model = method == "CPHARD"
    run_hard_ilp_model = method == "ILPHARD"

    # Set time limit for the solver (default 10 minutes)
    timelimit = 30 * 60
    if len(sys.argv) > 3 and sys.argv[3] != "-":
        timelimit = int(sys.argv[3])

    # Set minimum preferences per kid (default 1)
    min_prefs_per_kid = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    # Set deviation to 10% (default 0.1)
    deviation = float(sys.argv[5]) if len(sys.argv) > 5 else 0.1

    # Define paths
    processed_data_folder = 'data/processed_data'

    # Run pipeline
    run_pipeline()


