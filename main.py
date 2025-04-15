import pandas as pd
import os
import shutil

from code.anonymize_data import run_anonymize
from code.validate_data import validate_grouping_data
from code.baseline_random import run_random_baseline
from help_functions import read_df


def read_group_preferences():
    df = read_df(school, processed_data_folder, 'group_preferences.csv')
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2 = df.iloc[0]

    # Check if all values exist
    if pd.isnull(n_students) or pd.isnull(n_groups) or pd.isnull(min_group_size) or pd.isnull(max_extra_care_1) or pd.isnull(max_extra_care_2):
        raise ValueError("One or more values in group preferences are missing.")

    return n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2



def run_pipeline():
    # Anonymize data for the specified school
    run_anonymize(school, raw_data_folder, processed_data_folder)

    # Read group preferences
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2 = read_group_preferences()

    # Validate grouping input data
    is_valid = validate_grouping_data(school, processed_data_folder, n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2)
    if is_valid == False:
        school_processed_folder = os.path.join(processed_data_folder, school)
        if os.path.exists(school_processed_folder):
            shutil.rmtree(school_processed_folder)

        exit("Grouping data is invalid. Please check the errors above.")

    # Run random grouping algorithm
    if run_baseline_random:
        run_random_baseline(school, processed_data_folder)




if __name__ == "__main__":
    # Define variables for this run
    school = 'school_1'
    random_seed = 42
    run_baseline_random = True
    run_baseline_ilp = False
    run_cp = False

    # Define paths
    raw_data_folder = 'data/raw_data'
    processed_data_folder = 'data/processed_data'

    # Run pipeline
    run_pipeline()


