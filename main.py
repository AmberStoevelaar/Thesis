from code.models.baseline_random import run_random_baseline
from code.models.ILP import run_ilp
from code.models.CP import run_cp
from code.models.greedy import run_greedy
# from code.models.baseline_random2 import run_greedy

import sys

def run_pipeline():
    print("Running pipeline for school: {}".format(school))

    # Run random grouping algorithm
    if run_baseline_greedy:
        run_greedy(school, processed_data_folder)

    # Run ILP algorithm
    if run_baseline_ilp:
        run_ilp(school, processed_data_folder, timelimit, min_prefs_per_kid)

    # Run CP algorithm
    if run_cp_model:
        run_cp(school, processed_data_folder, timelimit, min_prefs_per_kid)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 main.py <school> <method: cp|ilp|greedy> [min_prefs_per_kid] [timelimit]")
        sys.exit(1)

    school = sys.argv[1]
    method = sys.argv[2].lower()
    random_seed = 42

    # Set which model to run
    run_baseline_greedy = method == "greedy"
    run_baseline_ilp = method == "ilp"
    run_cp_model = method == "cp"

    # Set minimum preferences per kid (default 1)
    min_prefs_per_kid = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    # Set time limit for the solver (default 10 minutes)
    timelimit = int(sys.argv[4]) if len(sys.argv) > 4 else 10*60


    # Define paths
    processed_data_folder = 'data/processed_data'

    # Run pipeline
    run_pipeline()


