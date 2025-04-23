import pandas as pd
import os
import numpy as np

def read_df(school, processed_data_folder, filename):
    path = os.path.join(processed_data_folder, school, filename)
    return pd.read_csv(path)

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

def create_preference_matrix(info_students, n_students):
    preference_matrix = np.zeros((n_students, n_students))
    students = info_students['Student'].tolist()

    for i in range(n_students):
        preferences_i = info_students.loc[info_students['Student'] == students[i],
                                        ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']].values.flatten().tolist()
        preferences_i = [p for p in preferences_i if pd.notna(p)]

        for j in range(n_students):
            if i == j:
                continue

            # Only one sided preferences
            if students[j] in preferences_i:
                preference_matrix[i][j] = 1

    return preference_matrix



