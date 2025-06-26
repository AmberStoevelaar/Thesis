import pandas as pd
import os

class InputData:
    def __init__(self, group_preferences, info_students, info_teachers, constraints_students, constraints_teachers, current_groups):
        self.group_preferences = group_preferences
        self.info_students = info_students
        self.info_teachers = info_teachers
        self.constraints_students = constraints_students
        self.constraints_teachers = constraints_teachers
        self.current_groups = current_groups

class Groupvariables:
    def __init__(self, n_students, n_groups, min_group_size, max_extra_care, max_group_size):
        self.n_students = n_students
        self.n_groups = n_groups
        self.min_group_size = min_group_size
        self.max_extra_care = max_extra_care
        self.max_group_size = max_group_size

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

def read_dfs(school, processed_data_folder):
    return InputData(
        read_df(school, processed_data_folder, 'group_preferences.csv'),
        read_df(school, processed_data_folder, 'info_students.csv'),
        read_df(school, processed_data_folder, 'info_teachers.csv'),
        read_df(school, processed_data_folder, 'constraints_students.csv'),
        read_df(school, processed_data_folder, 'constraints_teachers.csv'),
        read_df(school, processed_data_folder, 'current_groups.csv')
    )

def read_variables(data):
    group_preferences = data.group_preferences
    n_students, n_groups, min_group_size, max_extra_care = group_preferences.iloc[0]
    max_group_size = get_max_group_size(min_group_size, n_students, n_groups)
    return Groupvariables(n_students, n_groups, min_group_size, max_extra_care, max_group_size)


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

def create_preference_matrix(data, variables):
    students = data.info_students['Student'].tolist()
    preference_matrix = pd.DataFrame(0, index=students, columns=students)

    for i in range(variables.n_students):
        preferences_i = data.info_students.loc[data.info_students['Student'] == students[i],
                                          ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']].values.flatten().tolist()
        preferences_i = [p for p in preferences_i if pd.notna(p)]

        for j in range(variables.n_students):
            if i == j:
                continue

            if students[j] in preferences_i:
                preference_matrix.loc[students[i], students[j]] = 1

    return preference_matrix

# MODELS
def estimated_max_prefs(preferences, students, teachers):
    # Sum the total number of peer preferences, scaled by how many teachers
    return sum(preferences.loc[s].sum() * len(teachers) for s in students) or 1

def estimated_max_fairness(fairness_layers):
    # Exponentially weighted total fairness score across all layers
    max_k = max((k for k, _ in fairness_layers), default=1)
    return sum(10 ** (max_k - k) for k, _ in fairness_layers) or 1

def estimated_max_balance_penalty(data, attributes_to_balance, teachers):
    # Maximum possible deviation if all students of a type go to one teacher
    total_penalty = 0
    num_teachers = len(teachers)
    for attr in attributes_to_balance:
        counts = data.info_students[attr].value_counts()
        for value_count in counts.values:
            ideal = value_count / num_teachers
            total_penalty += abs(value_count - ideal)
    return total_penalty or 1
