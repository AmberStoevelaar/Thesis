import pandas as pd
import os
import sys
import json
import numpy as np
import re

try:
    from .helpers import get_minimum_preferences_satisfied
    from .save_results import save_to_excel
except ImportError:
    from helpers import get_minimum_preferences_satisfied
    from save_results import save_to_excel

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from helpers import read_dfs, read_variables

# TOTAL PREFERENCES
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

# BALANCE
def get_balance(df, attribute, group_col='Assigned Group'):
    result = {}
    values = df[attribute].dropna().unique()

    for value in values:
        subset = df[df[attribute] == value]

        # Counts and percentages of groups for this attribute value
        group_counts = subset[group_col].value_counts()
        group_percentages = subset[group_col].value_counts(normalize=True)

        # Build inner dict with counts and percentages
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

def ideal_distribution(total, groups):
    base = total // groups
    remainder = total % groups
    return [base + 1] * remainder + [base] * (groups - remainder)

def actual_distribution(details):
    return [details[g]["count"] for g in details if g != "total"]

def compute_normalized_balance_deviation(balance_dict, group_sizes):
    deviations = {}
    groups = len(group_sizes)

    for attribute, values in balance_dict.items():
        total_deviation = 0
        for _, details in values.items():
            total = details["total"]
            if total == 0:
                # Avoid divide by 0
                continue
            ideal = ideal_distribution(total, groups)
            actual = actual_distribution(details)
            deviation = sum(abs(a - i) for a, i in zip(actual, ideal))
            total_deviation += deviation / total

        deviations[attribute] = total_deviation

    deviations["total"] = sum(deviations.values())
    return deviations

# EFFICIENCY
def add_efficiency(school, method, timestamp, evaluation_results):
    logs_folder = os.path.join("data/results", school, method, "logs")
    log_path = os.path.join(logs_folder, f"{method}_{timestamp}.csv")

    if os.path.exists(log_path):
        logs_df, final_status_line = load_log_file_cleaned(log_path)
        # Drop any rows that are not data
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

# MINIMUM PREFERENCES/ FAIRNESS
def only_minimum_satisfied(df):
    columns = ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']
    min_satisfied = get_minimum_preferences_satisfied(df)

    count_min = 0
    count_above_min = 0
    eligible_students = 0

    for _, row in df.iterrows():
        student_group = row['Assigned Group']
        preferences = row[columns].dropna().tolist()
        satisfied = 0

        for pref_student in preferences:
            if pd.isna(pref_student):
                continue
            # Find group of preferred student
            match = df[df['Student'] == pref_student]
            if not match.empty and match['Assigned Group'].values[0] == student_group:
                satisfied += 1

        if len(preferences) > min_satisfied:
            eligible_students += 1
            if satisfied == min_satisfied:
                count_min += 1
            elif satisfied > min_satisfied:
                count_above_min += 1

    percentage_min = count_min / eligible_students if eligible_students > 0 else 0.0
    percentage_above_min = count_above_min / eligible_students if eligible_students > 0 else 0.0

    return (count_min, percentage_min), (count_above_min, percentage_above_min)

# SAVE EVALUATION RESULTS
def convert_keys_to_native(obj):
    # Convert to python integers
    if isinstance(obj, dict):
        return {int(k) if isinstance(k, (np.integer,)) else k: convert_keys_to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_keys_to_native(i) for i in obj]
    else:
        return obj

def load_log_file_cleaned(log_path):
    with open(log_path, 'r') as file:
        lines = file.readlines()

    # Find the line where the header starts
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

def save_evaluation(school, method, results_dict, timestamp):
    results_dict = convert_keys_to_native(results_dict)

    output_folder = os.path.join("data/results", school, method, "evaluation")
    os.makedirs(output_folder, exist_ok=True)

    output_path = os.path.join(output_folder,f"{method}_{timestamp}.json")
    with open(output_path, "w") as f:
        json.dump(results_dict, f, indent=4)

# RUN EVALUATION
def run_evaluate(school, processed_data_folder, method, groups, timestamp):

    processed_data_folder = "data/processed_data/"
    data = read_dfs(school, processed_data_folder)

    # Merge dataframes
    merged = pd.merge(groups, data.info_students, on='Student', how='left')
    merged.rename(columns={'Teacher': 'Assigned Group'}, inplace=True)

    (min_count, min_percentage), (above_min_count, above_min_percentage) = only_minimum_satisfied(merged)

    evaluation_results = {
        "preferences_satisfied": get_total_preferences_satisfied(merged),
        "satisfaction_rate": get_satisfaction_rate(merged),
        "minimum_preferences": get_minimum_preferences_satisfied(merged),
        "only_minimum_satisfied": min_count,
        "only_minimum_percentage": min_percentage,
        "more_than_minimum_satisfied": above_min_count,
        "more_than_minimum_percentage": above_min_percentage
    }

    group_sizes = merged['Assigned Group'].value_counts().sort_index().to_dict()
    evaluation_results["group_sizes"] = group_sizes

    # Balance
    balance = {}
    categorical_attributes = ['Gender', 'Grade', 'Extra Care', 'Behavior']

    for attr in categorical_attributes:
        if attr in merged.columns:
            balance[attr] = get_balance(merged, attr)

    evaluation_results["group_balance"] = balance

    deviation_results = compute_normalized_balance_deviation(balance, group_sizes)
    evaluation_results["balance_deviation"] = deviation_results
    evaluation_results["total_deviation"] = sum(deviation_results.values())

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
