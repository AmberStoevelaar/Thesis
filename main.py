import pandas as pd
import os

from code.anonymize_data import run_anonymize

def read_group_preferences(school, processed_data_folder):
    path = os.path.join(processed_data_folder, school)
    group_preferences_path = os.path.join(path, 'group_preferences.csv')

    df = pd.read_csv(group_preferences_path)
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2 = df.iloc[0]

    return n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2


if __name__ == "__main__":
    school = 'school_1'

    # Define paths
    raw_data_folder = 'data/raw_data'
    processed_data_folder = 'data/processed_data'


    # --------------------------------------------------------------------------
    # Starting pipeline
    # --------------------------------------------------------------------------

    # Anonymize data for the specified school
    run_anonymize(school, raw_data_folder, processed_data_folder)

    # Read group preferences
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2 = read_group_preferences(school, processed_data_folder)




