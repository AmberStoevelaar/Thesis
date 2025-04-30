import os
import pandas as pd

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

def get_max_group_size(min_group_size, n_students, n_groups):
    remaining = n_students - ( min_group_size * n_groups)
    max_size = min_group_size + (remaining // n_groups)
    if remaining % n_groups != 0:
        max_size += 1
    return max_size

class InputData:
    def __init__(self, group_preferences, info_students, info_teachers, constraints_students, constraints_teachers):
        self.group_preferences = group_preferences
        self.info_students = info_students
        self.info_teachers = info_teachers
        self.constraints_students = constraints_students
        self.constraints_teachers = constraints_teachers

class Groupvariables:
    def __init__(self, n_students, n_groups, min_group_size, max_extra_care, max_group_size):
        self.n_students = n_students
        self.n_groups = n_groups
        self.min_group_size = min_group_size
        self.max_extra_care = max_extra_care
        self.max_group_size = max_group_size

def read_dfs(school, processed_data_folder):
    return InputData(
        read_df(school, processed_data_folder, 'group_preferences.csv'),
        read_df(school, processed_data_folder, 'info_students.csv'),
        read_df(school, processed_data_folder, 'info_teachers.csv'),
        read_df(school, processed_data_folder, 'constraints_students.csv'),
        read_df(school, processed_data_folder, 'constraints_teachers.csv')
    )

def read_variables(data):
    group_preferences = data.group_preferences
    n_students, n_groups, min_group_size, max_extra_care = group_preferences.iloc[0]
    max_group_size = get_max_group_size(min_group_size, n_students, n_groups)
    return Groupvariables(n_students, n_groups, min_group_size, max_extra_care, max_group_size)

