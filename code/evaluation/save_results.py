import pandas as pd
import os

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
        satisfied_with_list.append(", ".join(map(str, student_result["satisfied_with"])))  # as string

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




def save_to_excel(df, school, method, timestamp):
    # Add number of preferences satisfied and satisfied with columns
    df = update_df(df)

    # Create a directory for the results if it doesn't exist
    solution_folder = os.path.join("data/results", school, method, "solutions")
    os.makedirs(solution_folder, exist_ok=True)

    filename = os.path.join(solution_folder, f"{method}_{timestamp}.xlsx")

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # sheet 1: satisfied preferences
        df.to_excel(writer, index=False, sheet_name='Student info')

        # sheet 2: final groups
        if 'Assigned Group' in df.columns:
            teacher_df = create_teacher_student_df_from_df(df)
            teacher_df.to_excel(writer, index=False, sheet_name='Groups')








