import pandas as pd
import os
import json

def get_preferences_satisfied_per_student(df):
    columns = ['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']
    results = {}

    for _, row in df.iterrows():
        student = row['Student']
        student_group = row['Assigned Group']
        prefs = [p for p in row[columns].tolist() if pd.notna(p)]

        satisfied = []
        for pref_student in prefs:
            try:
                pref_group = df.loc[df['Student'] == pref_student, 'Assigned Group'].values[0]
                if pref_group == student_group:
                    satisfied.append(pref_student)
            except IndexError:
                # In case the preferred student is not in the dataframe
                continue

        results[student] = {
            "num_satisfied": len(satisfied),
            "satisfied_with": satisfied
        }

    return results

def update_df(df):
    results = get_preferences_satisfied_per_student(df)
    num_satisfied_list = []
    satisfied_with_list = []

    for _, row in df.iterrows():
        student = row['Student']
        student_result = results.get(student, {"num_satisfied": 0, "satisfied_with": []})
        num_satisfied_list.append(student_result["num_satisfied"])
        satisfied_with_list.append(", ".join(map(str, student_result["satisfied_with"])))

    df['Num Preferences'] = num_satisfied_list
    df['Matched Preferences'] = satisfied_with_list

    return df

def create_teacher_student_df_from_df(df):
    teacher_groups = df.groupby('Assigned Group')['Student'].apply(list).to_dict()

    # Find max group size for padding
    max_students = max(len(students) for students in teacher_groups.values())

    # Pad each group so columns are even length
    padded = {
        teacher: students + [''] * (max_students - len(students))
        for teacher, students in teacher_groups.items()
    }

    return pd.DataFrame(padded)

def prettify_subcategory(category, subcat):
    if category == "Gender":
        if subcat.lower() == "boy":
            return "Boys"
        elif subcat.lower() == "girl":
            return "Girls"
        else:
            return subcat
    elif category == "Grade":
        return f"Group {subcat}"
    elif category == "Extra Care":
        if subcat.lower() == "yes":
            return "Extra Care"
    elif category == "Behavior":
        if subcat.lower() == "yes":
            return "Behavior"
    elif category == "Learning":
        if subcat.lower() == "yes":
            return "Learning"
    elif category == "Combination":
        if subcat.lower() == "yes":
            return "Combination"
    else:
        return subcat

def create_balance_df(evaluation):
    data = {}
    group_names = list(evaluation['group_sizes'].keys())

    group_sizes_row = [evaluation['group_sizes'][group] for group in group_names]
    data["Group Size"] = group_sizes_row

    for category, subcats in evaluation['group_balance'].items():
        for subcat, group_info in subcats.items():
            if subcat.lower() == "no":
                # Skip all 'No' subcategories entirely
                continue

            col_name = prettify_subcategory(category, subcat)
            if col_name is None:
                continue

            # Collect counts per group
            counts = []
            for group in group_names:
                counts.append(group_info.get(group, {}).get('count', 0))
            data[col_name] = counts

    df = pd.DataFrame.from_dict(data, orient='index', columns=group_names)
    return df


def save_to_excel(df, school, method, timestamp):
    # Add number of preferences satisfied and satisfied with columns
    df = update_df(df)

    # Create a directory for the results if it doesn't exist
    solution_folder = os.path.join("data/results", school, method, "solutions")
    os.makedirs(solution_folder, exist_ok=True)

    # Load evaluation
    eval_path = os.path.join("data/results", school, method, "evaluation", f"{method}_{timestamp}.json")
    with open(eval_path, 'r') as f:
        evaluation = json.load(f)

    filename = os.path.join(solution_folder, f"{method}_{timestamp}.xlsx")

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # sheet 1: satisfied preferences
        df.to_excel(writer, index=False, sheet_name='Student info')

        # sheet 2: final groups
        if 'Assigned Group' in df.columns:
            teacher_df = create_teacher_student_df_from_df(df)
            teacher_df.to_excel(writer, index=False, sheet_name='Groups')

        # sheet 3: balance
        balance_df = create_balance_df(evaluation)
        balance_df.to_excel(writer, sheet_name='Group details')
