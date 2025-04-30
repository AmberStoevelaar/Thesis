import pandas as pd
import os
from check_constraints import run_check_constraints
from results_overview import show_counts
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from help_functions import read_dfs, read_variables


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

# TODO checken hoe goed dit werkt
def get_minimum_preferences_satisfied(df):
    columns = ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']
    min_satisfied = float('inf')

    for _, row in df.iterrows():
        student = row['Student']
        student_group = row['Assigned Group']
        prefs = row[columns].tolist()

        # Count how many preferences were provided
        prefs_provided = [p for p in prefs if not pd.isna(p)]
        n_provided = len(prefs_provided)

        if n_provided == 0:
            continue  # Skip students with no preferences

        # Count how many preferences were satisfied
        n_satisfied = 0
        for pref_student in prefs_provided:
            pref_group = df.loc[df['Student'] == pref_student, 'Assigned Group'].values[0]
            if pref_group == student_group:
                n_satisfied += 1

        # Update minimum satisfied if it's lower
        min_satisfied = min(min_satisfied, n_satisfied)

    return min_satisfied if min_satisfied != float('inf') else 0


# def evaluate_accuracy_from_csv(assigned_groups, preferences_df):
#     total_points = 0
#     student_groups = assigned_groups.set_index('ID')['Assigned_Group'].to_dict()

#     for _, row in preferences_df.iterrows():
#         student_id = row['ID']
#         preferences = row[['Preference_1', 'Preference_2', 'Preference_3', 'Preference_4', 'Preference_5']].dropna().tolist()

#         assigned_group = student_groups.get(student_id)

#         student_score = 0
#         for i, preferred_student in enumerate(preferences):
#             if preferred_student in student_groups and student_groups[preferred_student] == assigned_group:
#                 student_score += (5 - i)

#         total_points += student_score

#     optimal_score = calculate_optimal_score(preferences_df)

#     if optimal_score == 0:
#         relative_excess = 0
#     else:
#         relative_excess = (optimal_score - total_points) / optimal_score * 100

#     absolute_difference = optimal_score - total_points
#     return total_points, optimal_score, relative_excess, absolute_difference


# # Evaluate the accuracy
# total_points, optimal_score, relative_excess, absolute_difference = evaluate_accuracy_from_csv(assigned_groups, preferences)

# print("Total Points:", total_points)
# print("Optimal Score:", optimal_score)
# print("Absolute Difference:", absolute_difference)
# print("Relative Excess (%):", relative_excess)



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
    min_preferences = get_minimum_preferences_satisfied(merged)
    print(f"Minimum preferences satisfied: {min_preferences}")




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

    show_counts(merged)
    run_evaluation(merged, data, variables)

























