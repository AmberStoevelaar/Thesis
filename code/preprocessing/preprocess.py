import os
import pandas as pd
import shutil
import sys

from anonymize_data import run_anonymize
from validate_data import validate_grouping_data

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from help_functions import read_group_preferences


def run_preprocess(raw_data_folder, processed_data_folder):
    for school in os.listdir(raw_data_folder):
        print("Running preprocessing for school: {}".format(school))

        if school == '.DS_Store' or school == 'school_1':
            print("Skipping file: {}".format(school))
            continue

        run_anonymize(school, raw_data_folder, processed_data_folder)

        # Validate grouping input data
        is_valid = validate_grouping_data(school, processed_data_folder)
        if is_valid == False:
            school_processed_folder = os.path.join(processed_data_folder, school)
            if os.path.exists(school_processed_folder):
                shutil.rmtree(school_processed_folder)

            exit("Grouping data is invalid. Please check the errors above.")
        else:
            print("Grouping data is valid.")


if __name__ == "__main__":
    # Define paths
    raw_data_folder = 'data/raw_data'
    processed_data_folder = 'data/processed_data'

    # Run preprocessing
    run_preprocess(raw_data_folder, processed_data_folder)





