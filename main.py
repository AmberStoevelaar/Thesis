from code.baseline_random import run_random_baseline
from code.MILP2 import run_milp
from code.CP import run_cp

import sys


def run_pipeline():
    print("Running pipeline for school: {}".format(school))

    # Run random grouping algorithm
    if run_baseline_random:
        run_random_baseline(school, processed_data_folder)

    # Run ILP algorithm
    if run_baseline_ilp:
        run_milp(school, processed_data_folder)

    # Run CP algorithm
    if run_cp_model:
        run_cp(school, processed_data_folder)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 main.py <school> <method: cp|milp|random> [random_seed]")
        sys.exit(1)

    school = sys.argv[1]
    method = sys.argv[2].lower()
    random_seed = 42

    # Set which model to run
    run_baseline_random = method == "random"
    run_baseline_ilp = method == "milp"
    run_cp_model = method == "cp"

    # Change seed if random method is selected and seed is provided
    if run_baseline_random and len(sys.argv) >= 4:
        try:
            random_seed = int(sys.argv[3])
        except ValueError:
            print("Random seed must be an integer.")
            sys.exit(1)

    # Define paths
    processed_data_folder = 'data/processed_data'

    # Run pipeline
    run_pipeline()


