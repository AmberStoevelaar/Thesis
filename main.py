import os

from code.models.baseline_random import run_random_baseline
from code.models.ILP import run_ilp
# from code.models.CP import run_cp
from code.models.CPsoft import run_cp
# from code.models.greedy import run_greedy
# from code.models.baseline_random2 import run_greedy
from code.models.baseline_random import run_random_baseline
from code.evaluation.evaluate_results import run_evaluate

import sys

def save_results(results, timestamp):
    folder = 'data/results'
    results_folder = os.path.join(folder, school, method)

    solution_folder = os.path.join(results_folder, "solutions")
    print(f"Saving results to {solution_folder}")
    os.makedirs(solution_folder, exist_ok=True)

    output_file = os.path.join(solution_folder, f"{method}_{timestamp}.csv")
    results.to_csv(output_file, index=False)


# def evaluate_results(results):
#     pass


def run_pipeline():
    print("Running pipeline for school: {}".format(school))

    results = None
    timestamp = None

    # Run random grouping algorithm
    # TODO: not only fix model but also folder struxture
    if run_baseline_greedy:
        run_random_baseline(school, processed_data_folder)
        # run_greedy(school, processed_data_folder, min_prefs_per_kid, deviation)

    # Run ILP algorithm
    if run_baseline_ilp:
        results, timestamp = run_ilp(school, processed_data_folder, timelimit, min_prefs_per_kid, deviation)

    # Run CP algorithm
    if run_cp_model:
        results, timestamp = run_cp(school, processed_data_folder, timelimit)


    if results is not None:
        # Save results
        save_results(results, timestamp)
        # Evaluate results
        run_evaluate(school, processed_data_folder, method, results, timestamp)




if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 main.py <school> <method: cp|ilp|greedy> [min_prefs_per_kid] [deviation] [timelimit]")
        sys.exit(1)

    school = sys.argv[1]
    method = sys.argv[2].upper()
    random_seed = 42

    # Set which model to run
    run_baseline_greedy = method == "GREEDY"
    run_baseline_ilp = method == "ILP"
    run_cp_model = method == "CP"

    # Set minimum preferences per kid (default 1)
    min_prefs_per_kid = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    # Set deviation to 10% (default 0.1)
    deviation = float(sys.argv[4]) if len(sys.argv) > 4 else 0.1

    # Set time limit for the solver (default 10 minutes)
    timelimit = int(sys.argv[5]) if len(sys.argv) > 5 else 10*60

    # Define paths
    processed_data_folder = 'data/processed_data'

    # Run pipeline
    run_pipeline()


