import pandas as pd
import os

def read_df(school, processed_data_folder, file_name):
    path = os.path.join(processed_data_folder, school)
    file_path = os.path.join(path, file_name)
    df = pd.read_csv(file_path)
    return df

def read_group_preferences(school, processed_data_folder):
    df = read_df(school, processed_data_folder, 'group_preferences.csv')
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2 = df.iloc[0]

    # Check if all values exist
    if pd.isnull(n_students) or pd.isnull(n_groups) or pd.isnull(min_group_size) or pd.isnull(max_extra_care_1) or pd.isnull(max_extra_care_2):
        raise ValueError("One or more values in group preferences are missing.")

    return n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2

def get_max_group_size(min_group_size, n_students, n_groups):
    remaining = n_students - ( min_group_size * n_groups)
    max_size = min_group_size + (remaining // n_groups)
    if remaining % n_groups != 0:
        max_size += 1
    return max_size

def get_assigned_students(groups):
    return [student for group in groups.values() for student in group]

def is_assigned(student, groups):
    if student in get_assigned_students(groups):
        return True
    return False

def get_group(student, groups):
    group = [group for group in groups if student in groups[group]]
    return group[0]