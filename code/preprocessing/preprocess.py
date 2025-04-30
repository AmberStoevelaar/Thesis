import os
import pandas as pd
import shutil

from anonymize_data import run_anonymize
from validate_data import validate_grouping_data

def read_df(school, processed_data_folder, filename):
    path = os.path.join(processed_data_folder, school, filename)
    return pd.read_csv(path)

def read_group_preferences(school, processed_data_folder):
    df = read_df(school, processed_data_folder, 'group_preferences.csv')
    n_students, n_groups, min_group_size, max_extra_care = df.iloc[0]

    # Check if all values exist
    if pd.isnull(n_students) or pd.isnull(n_groups) or pd.isnull(min_group_size) or pd.isnull(max_extra_care):
        raise ValueError("One or more values in group preferences are missing.")

    return n_students, n_groups, min_group_size, max_extra_care



def run_preprocess(raw_data_folder, processed_data_folder):
    for school in os.listdir(raw_data_folder):
        print("Running preprocessing for school: {}".format(school))

        if school == '.DS_Store' or school == 'school_1':
            print("Skipping file: {}".format(school))
            continue

        run_anonymize(school, raw_data_folder, processed_data_folder)

        # Read group preferences
        n_students, n_groups, min_group_size, max_extra_care = read_group_preferences(school, processed_data_folder)

        # Validate grouping input data
        is_valid = validate_grouping_data(school, processed_data_folder, n_students, n_groups, min_group_size, max_extra_care)
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





