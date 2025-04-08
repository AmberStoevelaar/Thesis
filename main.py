import os

from code.anonymize_data import run_anonymize





if __name__ == "__main__":
    school = 'school_1'

    # Anonymize data for the specified school
    raw_data_folder = 'data/raw_data'
    processed_data_folder = 'data/processed_data'
    run_anonymize(school, raw_data_folder, processed_data_folder)



