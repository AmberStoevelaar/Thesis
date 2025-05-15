import pandas as pd
import os
from check_constraints import run_check_constraints
from results_overview import show_counts
import sys

from helpers import get_satisfied_preferences_per_student, get_minimum_preferences_satisfied

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


def get_average_preferences(df):
    total_preferences_satisfied = get_total_preferences_satisfied(df)
    total_students = len(df)
    average_preferences = total_preferences_satisfied / total_students
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


def evaluate_accuracy_from_csv(df):
    score = get_total_preferences_satisfied(df)

    # Optimal score is the total number of preferences provided?
    optimal_score = get_total_preferences_provided(merged)

    print(f"Score: {score}")
    print(f"Optimal score: {optimal_score}")

    relative_excess = (optimal_score - score) / optimal_score * 100
    absolute_difference = abs(optimal_score - score)
    return relative_excess, absolute_difference


def run_evaluation(merged, data, variables):
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
    relative_excess, absolute_difference = evaluate_accuracy_from_csv(merged)
    print(f"Relative excess: {relative_excess:.2f}%")
    print(f"Absolute difference: {absolute_difference}")


if __name__ == "__main__":
    # Get method from command-line argument
    if len(sys.argv) < 2:
        print("Usage: python3 filename.py [ilp|cp|greedy]")
        sys.exit(1)

    method = sys.argv[1].lower()
    method_folder = method.upper() if method in ["ilp", "cp"] else method.capitalize()

    results_folder = "data/results/"
    processed_data_folder = "data/processed_data/"

    # school = "school_1"
    # filename = "CP_20250429_121259.csv"
    school = "vorige"
    # filename = "ILP_13-05_10:58.csv"
    filename= "Greedy_15-05_12:47.csv"
    # filename = "vorige.csv"

    # Read in all necessary files
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)
    groups = pd.read_csv(os.path.join(results_folder, school, method_folder, filename))

    # Merge dataframes
    merged = pd.merge(groups, data.info_students, on='Student', how='left')
    merged.rename(columns={'Teacher': 'Assigned Group'}, inplace=True)

    # show_counts(merged)
    get_satisfied_preferences_per_student(merged)
    run_evaluation(merged, data, variables)

























