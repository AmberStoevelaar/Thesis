import pandas as pd
import os
from check_constraints import run_check_constraints

# # Count the number of students in each group
# group_counts = assigned_groups['Assigned Group'].value_counts().sort_index()

# # Count gender in each Assigned_Group
# gender_counts = merged.groupby("Assigned Group")["Gender"].value_counts().unstack().fillna(0)

# # Count Group (4/5) in each Assigned_Group
# grade_counts = merged.groupby("Assigned Group")["Group"].value_counts().unstack().fillna(0)

# print("Number of students in each group:")
# print(group_counts)

# print("Gender count per assigned group:")
# print(gender_counts)

# print("\Grade count per assigned group:")
# print(grade_counts)


# HULP FUNCTIES
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

class InputData:
    def __init__(self, group_preferences, info_students, info_teachers, constraints_students, constraints_teachers):
        self.group_preferences = group_preferences
        self.info_students = info_students
        self.info_teachers = info_teachers
        self.constraints_students = constraints_students
        self.constraints_teachers = constraints_teachers

class Groupvariables:
    def __init__(self, n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2, max_group_size):
        self.n_students = n_students
        self.n_groups = n_groups
        self.min_group_size = min_group_size
        self.max_extra_care_1 = max_extra_care_1
        self.max_extra_care_2 = max_extra_care_2
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
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2 = group_preferences.iloc[0]
    max_group_size = get_max_group_size(min_group_size, n_students, n_groups)
    return Groupvariables(n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2, max_group_size)



# ANDERE FUNCTIES
def get_total_preferences_satisfied(df):
    columns = ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']
    total = 0

    for _, row in df.iterrows():
        student_group = row['Assigned Group']
        prefs = row[columns].tolist()
        # print(f'Student: {row["Student"]}, Assigned Group: {student_group}, Preferences: {prefs}')

        for pref_student in prefs:
            if pd.isna(pref_student):
                continue
            pref_group = df.loc[df['Student'] == pref_student, 'Assigned Group'].values[0]
            if pref_group == student_group:
                total += 1

    return total

def get_satisfied_preferences_per_student(df):
    columns = ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']
    preferences = {}

    for _, row in df.iterrows():
        student = row['Student']
        student_group = row['Assigned Group']
        prefs = row[columns].tolist()

        count = 0
        for pref_student in prefs:
            if pd.isna(pref_student):
                continue
            pref_group = df.loc[df['Student'] == pref_student, 'Assigned Group'].values[0]
            if pref_group == student_group:
                count += 1

        preferences[student] = count

    print(f"Preferences per student: {preferences}")
    return preferences

def get_average_preferences(df):
    total_preferences = get_total_preferences_satisfied(df)
    total_students = len(df)
    average_preferences = total_preferences / total_students
    return average_preferences

def get_total_preferences_provided(df):
    columns = ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']
    total_preferences = 0

    for _, row in df.iterrows():
        preferences_provided = row[columns].notna().sum()
        total_preferences += preferences_provided

    return total_preferences

def get_satisfaction_rate(df):
    provided = get_total_preferences_provided(df)
    satisfied = get_total_preferences_satisfied(df)
    return satisfied / provided











def run_evaluation(merged, data, variables):
    # pass
    # CHECK CONSTRAINTS
    # Check if all groups satisfy the constraints
    groups = data.info_teachers['Teacher'].tolist()
    if run_check_constraints(groups, merged, data, variables):
        print("All constraints are satisfied.")

    # SOLUTION QUALITY
    # Total preferences satisfied
    total_preferences = get_total_preferences_satisfied(merged)
    print(f"Total preferences satisfied: {total_preferences}")

    # Avg preferences satisfied
    avg_preferences = get_average_preferences(merged)
    print(f"Average preferences satisfied: {avg_preferences:.2f}")

    # Satisfaction rate
    satisfaction_rate = get_satisfaction_rate(merged)
    print(f"Satisfaction rate: {satisfaction_rate:.2f}")

    # Min preferences satisfied for all students with that many preferences





    # EXTRA SOLUTION QUALITY
    # Optimal solution (number of preferences provided by students) / or optimal solution?
    n_provided_preferences = get_total_preferences_provided(merged)
    print(f"Total preferences provided by all students: {n_provided_preferences}")

    # Absolute difference between preferences satisfied and preferences given

    # Relative excess of preferences satisfied

    # --- fixed cost?






if __name__ == "__main__":
    results_folder = "data/results/"
    # school = "school_1"
    # filename = "CP_20250429_121259.csv"
    school = "school_2"
    filename = "CP_20250429_121212.csv"
    processed_data_folder = "data/processed_data/"

    # Read in all necessary files
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)
    groups = pd.read_csv(os.path.join(results_folder, school, filename))

    # Merge dataframes
    merged = pd.merge(groups, data.info_students, on='Student', how='left')
    merged.rename(columns={'Teacher': 'Assigned Group'}, inplace=True)


    run_evaluation(merged, data, variables)

























