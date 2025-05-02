from code.baseline_random import run_random_baseline
# from code.MILP2 import run_milp
from code.MILP_callback import run_milp
from code.CP import run_cp

import sys


def run_pipeline(timelimit):
    print("Running pipeline for school: {}".format(school))

    # Run random grouping algorithm
    if run_baseline_random:
        run_random_baseline(school, processed_data_folder)

    # Run ILP algorithm
    if run_baseline_ilp:
        run_milp(school, processed_data_folder, timelimit)

    # Run CP algorithm
    if run_cp_model:
        run_cp(school, processed_data_folder, timelimit)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 main.py <school> <method: cp|milp|random> [timelimit]")
        sys.exit(1)

    school = sys.argv[1]
    method = sys.argv[2].lower()
    random_seed = 42

    # Set which model to run
    run_baseline_random = method == "random"
    run_baseline_ilp = method == "milp"
    run_cp_model = method == "cp"

    # Set time limit for the solver (default 10 minutes)
    timelimit = int(sys.argv[3]) if len(sys.argv) > 3 else 10*60

    # Define paths
    processed_data_folder = 'data/processed_data'

    # Run pipeline
    run_pipeline(timelimit)


