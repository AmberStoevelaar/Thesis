import pandas as pd
import os

def read_df(school, processed_data_folder, file_name):
    path = os.path.join(processed_data_folder, school)
    file_path = os.path.join(path, file_name)
    df = pd.read_csv(file_path)
    return df