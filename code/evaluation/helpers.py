import pandas as pd

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

    return preferences

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
            # Skip students with no preferences
            continue

        # Count how many preferences were satisfied
        n_satisfied = 0
        for pref_student in prefs_provided:
            pref_group = df.loc[df['Student'] == pref_student, 'Assigned Group'].values[0]
            if pref_group == student_group:
                n_satisfied += 1

        # Update minimum satisfied if it's lower
        min_satisfied = min(min_satisfied, n_satisfied)

    return min_satisfied if min_satisfied != float('inf') else 0
