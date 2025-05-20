import pandas as pd
import os
import sys
import json
import numpy as np
import re


try:
    from .helpers import get_satisfied_preferences_per_student, get_minimum_preferences_satisfied
    from .check_constraints import run_check_constraints
    from .results_overview import show_counts
    from .save_results import save_to_excel
except ImportError:
    from helpers import get_satisfied_preferences_per_student, get_minimum_preferences_satisfied
    from check_constraints import run_check_constraints
    from results_overview import show_counts
    from save_results import save_to_excel

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from help_functions import read_dfs, read_variables


def get_total_preferences_satisfied(df):
    columns = ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']
    total = 0

    for _, row in df.iterrows():
        student_group = row['Assigned Group']
        prefs = row[columns].tolist()

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
    optimal_score = get_total_preferences_provided(df)

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


def get_balance(df, attribute, group_col='Assigned Group'):
    result = {}
    values = df[attribute].dropna().unique()

    for value in values:
        subset = df[df[attribute] == value]

        # Counts and percentages of groups for this attribute value
        group_counts = subset[group_col].value_counts()
        group_percentages = subset[group_col].value_counts(normalize=True)

        # Build inner dict with counts and percentages
        # result[attribute][value] = {}
        result[value] = {
            "total": int(len(subset)),
        }

        for group, count in group_counts.items():
            percent = round(group_percentages[group], 2)
            result[value][group] = {
                "count": int(count),
                "percent": percent
            }

    return result

def convert_keys_to_native(obj):
    if isinstance(obj, dict):
        return {int(k) if isinstance(k, (np.integer,)) else k: convert_keys_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_keys_to_native(i) for i in obj]
    else:
        return obj

def load_log_file_cleaned(log_path):
    with open(log_path, 'r') as file:
        lines = file.readlines()

    # Find the line where the header starts (typically "Timestamp,...")
    start_idx = next((i for i, line in enumerate(lines) if line.startswith("Timestamp")), None)

    if start_idx is None:
        raise ValueError("No header line found in log file.")

    # Read from the header line onward
    cleaned_lines = lines[start_idx:]
    from io import StringIO
    cleaned_csv = StringIO("".join(cleaned_lines))

    # Load with pandas
    df = pd.read_csv(cleaned_csv)
    last_line = next((line.strip() for line in reversed(lines) if line.strip()), None)
    return df, last_line

def add_efficiency(school, method, timestamp, evaluation_results):
    logs_folder = os.path.join("data/results", school, method, "logs")
    log_path = os.path.join(logs_folder, f"{method}_{timestamp}.csv")

    if os.path.exists(log_path):
        # logs_df = pd.read_csv(log_path)
        logs_df, final_status_line = load_log_file_cleaned(log_path)
        # Drop any rows that are not data (e.g. config rows)
        logs_df = logs_df[logs_df["Solution #"].apply(lambda x: str(x).isdigit())]

        if not logs_df.empty:
            logs_df["Elapsed Time (s)"] = pd.to_numeric(logs_df["Elapsed Time (s)"], errors='coerce')
            first_feasible_time = logs_df["Elapsed Time (s)"].iloc[0]
            last_time = logs_df["Elapsed Time (s)"].iloc[-1]

            evaluation_results["time_to_first_feasible"] = float(first_feasible_time)
            evaluation_results["time_to_optimal_or_timeout"] = float(last_time)
            evaluation_results["objective"] = float(logs_df["Objective Value"].iloc[-1])

        if final_status_line.startswith("Status,"):
            status_value = final_status_line.split(",", 1)[-1].strip()
            evaluation_results["final_status"] = status_value

    return evaluation_results

def save_evaluation(school, method, results_dict, timestamp):
    results_dict = convert_keys_to_native(results_dict)

    output_folder = os.path.join("data/results", school, method, "evaluation")
    os.makedirs(output_folder, exist_ok=True)

    output_path = os.path.join(output_folder,f"{method}_{timestamp}.json")
    with open(output_path, "w") as f:
        json.dump(results_dict, f, indent=4)

def run_evaluate(school, processed_data_folder, method, groups, timestamp):

    processed_data_folder = "data/processed_data/"
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    # Merge dataframes
    merged = pd.merge(groups, data.info_students, on='Student', how='left')
    merged.rename(columns={'Teacher': 'Assigned Group'}, inplace=True)

    evaluation_results = {
        "preferences_satisfied": get_total_preferences_satisfied(merged),
        "average_preferences": get_average_preferences(merged),
        "satisfaction_rate": get_satisfaction_rate(merged),
        "minimum_preferences": get_minimum_preferences_satisfied(merged),
        # "total_preferences_provided": get_total_preferences_provided(merged)
    }

    group_sizes = merged['Assigned Group'].value_counts().sort_index().to_dict()
    evaluation_results["group_sizes"] = group_sizes

    print(f"Total preferences satisfied: {evaluation_results['preferences_satisfied']}")
    print(f"Average preferences: {evaluation_results['average_preferences']:.2f}")
    print(f"Satisfaction rate: {evaluation_results['satisfaction_rate']:.2f}")
    print(f"Minimum preferences satisfied: {evaluation_results['minimum_preferences']}")
    # print(f"Total preferences provided by all students: {evaluation_results['total_preferences_provided']}")

    # # Relative & absolute difference
    # rel_excess, abs_diff = evaluate_accuracy_from_csv(merged)
    # evaluation_results["relative_excess"] = rel_excess
    # evaluation_results["absolute_difference"] = abs_diff

    # Balances
    balance = {}
    categorical_attributes = ['Gender', 'Grade', 'Extra Care', 'Behavior']

    for attr in categorical_attributes:
        if attr in merged.columns:
            balance[attr] = get_balance(merged, attr)

    evaluation_results["group_balance"] = balance

    # Add efficiency metrics
    evaluation_results = add_efficiency(school, method, timestamp, evaluation_results)

    # Save evaluation results
    save_evaluation(school, method, evaluation_results, timestamp)

    # Save to Excel
    save_to_excel(merged, school, method, timestamp)


if __name__ == "__main__":
    # Get method from command-line argument
    if len(sys.argv) < 3:
        print("Usage: python3 filename.py <school> <method: [ilp|cp|greedy]>")
        sys.exit(1)

    school = sys.argv[1]
    method = sys.argv[2].upper()

    processed_data_folder = "data/processed_data/"
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    filename = "ILPSOFT_20-05_10:14.csv"
    # filename = "vorige.csv"
    solutions_folder = os.path.join("data/results", school, method, "solutions")
    path = os.path.join(solutions_folder, filename)
    groups = pd.read_csv(path)

    match = re.search(r"(\d{2}-\d{2}_\d{2}:\d{2})", filename)
    if match:
        # Extract the timestamp from the filename
        timestamp = match.group(1)
    else:
        timestamp = "unknown"

    print(f"Evaluating results for {school} using {method} with timestamp {timestamp}")

    # Run evaluation
    run_evaluate(school, processed_data_folder, method, groups, timestamp)


    # EXTRA
    # show_counts(merged)
    # get_satisfied_preferences_per_student(merged)



























