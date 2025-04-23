import pulp
import numpy as np
import pandas as pd
from dataclasses import dataclass

from help_functions import read_df, get_max_group_size

# Define variables for this run
def read_dfs(school, processed_data_folder):
    group_preferences = read_df(school, processed_data_folder, 'group_preferences.csv')
    info_students = read_df(school, processed_data_folder, 'info_students.csv')
    info_teachers = read_df(school, processed_data_folder, 'info_teachers.csv')
    constraints_students = read_df(school, processed_data_folder, 'constraints_students.csv')
    constraints_teachers = read_df(school, processed_data_folder, 'constraints_teachers.csv')

    return group_preferences, info_students, info_teachers, constraints_students, constraints_teachers

def read_variables(school, processed_data_folder, group_preferences):
    group_preferences, _, _, _, _ = read_dfs(school, processed_data_folder)
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2 = group_preferences.iloc[0]
    max_group_size = get_max_group_size(min_group_size, n_students, n_groups)

    return n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2, max_group_size

def get_gender_fractions(info_students, n_students, deviation):
    boys_dict = dict(zip(info_students['Student'], info_students['Gender'].apply(lambda x: 1 if x == 'Boy' else 0)))
    frac_boys = sum(boys_dict.values()) / len(boys_dict)
    min_frac_boys = max(frac_boys - deviation, 0)
    max_frac_boys = min(frac_boys + deviation, 1)

    print(f"Fraction boys min: {min_frac_boys}, max: {max_frac_boys}")
    return boys_dict, min_frac_boys, max_frac_boys

def get_year_fractions(info_students, n_students, deviation):
    years = info_students['Group'].unique()
    year_dicts = { year: dict(zip(info_students['Student'], (info_students['Group'] == year).astype(int))) for year in years}

    year_fracs = { year: (info_students['Group'] == year).sum() / n_students for year in years }
    year_bounds = { year: (max(frac - deviation, 0), min(frac + deviation, 1)) for year, frac in year_fracs.items() }

    return years , year_dicts, year_bounds

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



def add_constraints(ILO, school, processed_data_folder, x, y, y_group, deviation, min_prefs_per_student):
      # Read data
    group_preferences, info_students, info_teachers, constraints_students, constraints_teachers = read_dfs(school, processed_data_folder)
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2, max_group_size = read_variables(school, processed_data_folder, group_preferences)

    # Define students and teachers
    students = info_students['Student'].tolist()
    teachers = info_teachers['Teacher'].tolist()

    # Define the preference matrix
    preference_matrix = create_preference_matrix(info_students, n_students)

    # Define exclusions and inclusions
    exclusions_students = constraints_students[constraints_students['Together'] == 'No'][['Student 1', 'Student 2']].values.tolist()
    exclusions_teacher = constraints_teachers[constraints_teachers['Together'] == 'No'][['Student', 'Teacher']].values.tolist()
    inclusions_students = constraints_students[constraints_students['Together'] == 'Yes'][['Student 1', 'Student 2']].values.tolist()
    inclusions_teacher = constraints_teachers[constraints_teachers['Together'] == 'Yes'][['Student', 'Teacher']].values.tolist()

    # CONSTRAINTS
    # 2. Link y with y_group
    for s1 in students:
        for s2 in students:
            if s1 != s2:
                # ILO += y[s1][s2] == sum([y_group[s1][s2][t] for t in teachers]), f'set_y_{s1}_{s2}'
                ILO += y[s1][s2] == sum([y_group[s1][s2][t] for t in teachers if y_group[s1][s2][t] is not None]), f'set_y_{s1}_{s2}'

    for idx1, s1 in enumerate(students):
        for idx2 in range(idx1 + 1, len(students)):
            s2 = students[idx2]
            for t in teachers:
                ILO += y_group[s1][s2][t] <= (x[s1][t] + x[s2][t]) / 2, f'prop_1_y_group_{s1}_{s2}_{t}'
                ILO += y_group[s1][s2][t] >= x[s1][t] + x[s2][t] - 1, f'prop_2_y_group_{s1}_{s2}_{t}'

    # 1. Each student is assigned to exactly one teacher
    for s1 in students:
        ILO += pulp.lpSum([x[s1][t] for t in teachers]) == 1, f"Student_{s1}_assigned_once"
        # for s2 in students:
        #     if s1 != s2:
                # # 2. Link y with y_group
                # # ILO += y[s1][s2] == sum([y_group[s1][s2][t] for t in teachers]), f'set_y_{s1}_{s2}'
                # ILO += y[s1][s2] == sum([y_group[s1][s2][t] for t in teachers if y_group[s1][s2][t] is not None]), f'set_y_{s1}_{s2}'


                # # 3. Set y_group
                # for t in teachers:
                #     ILO += y_group[s1][s2][t] <= (x[s1][t] + x[s2][t]) / 2, f'prop_1_y_group_{s1}_{s2}_{t}'
                #     ILO += y_group[s1][s2][t] >= x[s1][t] + x[s2][t] - 1, f'prop_2_y_group_{s1}_{s2}_{t}'

    boys_dict, min_frac_boys, max_frac_boys = get_gender_fractions(info_students, n_students, deviation)
    years, year_dicts, year_bounds = get_year_fractions(info_students, n_students, deviation)

    for t in teachers:
        # 4. Each group has at least min_group_size and at most max_group_size students
        ILO += pulp.lpSum([x[s][t] for s in students]) >= min_group_size, f"Teacher_{t}_min_size"
        ILO += pulp.lpSum([x[s][t] for s in students]) <= max_group_size, f"Teacher_{t}_max_size"

        # 5. Each group has at least min_frac_boys and at most max_frac_boys
        ILO += pulp.lpSum([x[s][t] * boys_dict[s] for s in students]) >= min_frac_boys * pulp.lpSum([x[s][t] for s in students]), f"min_frac_boys_{t}"
        ILO += pulp.lpSum([x[s][t] * boys_dict[s] for s in students]) <= max_frac_boys * pulp.lpSum([x[s][t] for s in students]), f"max_frac_boys_{t}"

        # 6. Each group has at most max_extra_care_1 students with extra care 1
        # ILO += pulp.lpSum([x[s][t] * info_students.loc[info_students['Student'] == s, 'Extra Care'].values[0] for s in students]) <= max_extra_care_1, f"max_extra_care_1_{t}"
        extra_care_values = dict(zip(info_students['Student'], info_students['Extra Care'].map({'Yes': 1, 'No': 0})))
        ILO += pulp.lpSum([x[s][t] * extra_care_values[s] for s in students]) <= max_extra_care_1, f"max_extra_care_1_{t}"

        # 7. Each group has at most max_extra_care_2 students with extra care 2
        # ILO += pulp.lpSum([x[s][t] * info_students.loc[info_students['Student'] == s, 'Extra Care 2'].values[0] for s in students]) <= max_extra_care_2, f"max_extra_care_2_{t}"
        extra_care_2_values = dict(zip(info_students['Student'], info_students['Extra Care 2'].map({'Yes': 1, 'No': 0})))
        ILO += pulp.lpSum([x[s][t] * extra_care_2_values[s] for s in students]) <= max_extra_care_2, f"max_extra_care_2_{t}"

        for year in years:
            year_indicator = year_dicts[year]
            min_frac, max_frac = year_bounds[year]

            # 8. Each group has at least min_frac and at most max_frac students from each year
            ILO += (pulp.lpSum([x[s][t] * year_indicator[s] for s in students]) >= min_frac * pulp.lpSum([x[s][t] for s in students]), f"min_frac_{year}_{t}")
            ILO += (pulp.lpSum([x[s][t] * year_indicator[s] for s in students]) <= max_frac * pulp.lpSum([x[s][t] for s in students]), f"max_frac_{year}_{t}")

    # 9. Inclusions and exclusions
    # Exlusions between students
    for s1, s2 in exclusions_students:
        ILO += y[s1][s2] == 0, f'exclusion_{s1}_{s2}'

    # Exclusions between students and teachers
    for s, t in exclusions_teacher:
        ILO += x[s][t] == 0, f'exclusion_{s}_{t}'

    # Inclusions between students
    for s1, s2 in inclusions_students:
        ILO += y[s1][s2] == 1, f'inclusion_{s1}_{s2}'

    # Inclusions between students and teachers
    for s, t in inclusions_teacher:
        ILO += x[s][t] == 1, f'inclusion_{s}_{t}'

    # 10. Each student has at least min_prefs_per_student preferences
    has_preference = { s: int(any(preference_matrix[students.index(s)])) for s in students }
    for i, s in enumerate(students):
        total_prefs_matched = (
            pulp.lpSum([preference_matrix[i][j] * y[students[j]][s] for j in range(0, i)]) +
            pulp.lpSum([preference_matrix[i][j] * y[s][students[j]] for j in range(i + 1, n_students)])
        )
        ILO += total_prefs_matched >= min_prefs_per_student * has_preference[s], f'min_prefs_for_{s}'

    return ILO


def create_model(school, processed_data_folder, deviation, min_prefs_per_student):
    # # Read data
    group_preferences, info_students, info_teachers, constraints_students, constraints_teachers = read_dfs(school, processed_data_folder)
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2, max_group_size = read_variables(school, processed_data_folder, group_preferences)

    # Define students and teachers
    students = info_students['Student'].tolist()
    teachers = info_teachers['Teacher'].tolist()

    # Define the preference matrix
    preference_matrix = create_preference_matrix(info_students, n_students)

    student_index = {student: i for i, student in enumerate(students)}

    # Init model
    ILO = pulp.LpProblem("milp", pulp.LpMaximize)

    # DECISION VARIABLES
    # x[s][t] = 1 if student s assigned to teacher t
    x = {s: {t: pulp.LpVariable(f'x_{s}_{t}', cat='Binary') for t in teachers} for s in students}

    # y[s1][s2] = 1 if student s1 and s2 are in the same group (directional)
    y = {s1: {s2: pulp.LpVariable(f'y_{s1}_{s2}', cat='Binary') if s1 != s2 else None for s2 in students} for s1 in students}


    y_group = {
        s1: {s2: {t: pulp.LpVariable(f'y_{s1}_{s2}_{t}', cat='Binary') for t in teachers}
            for s2 in students}
        for s1 in students
    }

    # OBJECTIVE FUNCTION
    score = preference_matrix + preference_matrix.T
    # ILO += sum([y[s1][s2] * score[s1, s2] for s1 in students for s2 in students if s1 < s2]), "total_score"
    # Create a mapping from student names to indices
    # student_index = {student: i for i, student in enumerate(students)}

    # Now, when you access score, you can use the index of the student
    ILO += sum([y[s1][s2] * score[student_index[s1], student_index[s2]] for s1 in students for s2 in students if student_index[s1] < student_index[s2]]), "total_score"

    ILO = add_constraints(ILO, school, processed_data_folder, x, y, y_group, deviation, min_prefs_per_student)

    return ILO, x, y, y_group


def solve_model(ILO, x, y, y_group, school, processed_data_folder):
    # Read data
    group_preferences, info_students, info_teachers, constraints_students, constraints_teachers = read_dfs(school, processed_data_folder)
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2, max_group_size = read_variables(school, processed_data_folder, group_preferences)

    # Define students and teachers
    students = info_students['Student'].tolist()
    teachers = info_teachers['Teacher'].tolist()

    # Define the preference matrix
    preference_matrix = create_preference_matrix(info_students, n_students)

    student_index = {student: i for i, student in enumerate(students)}



    # Solve
    # ILO.solve(pulp.CBC_CMD(msg=True, timeLimit=30 * 60))
    # ILO.solve(pulp.PULP_CBC_CMD(msg=True, timeLimit=3 * 60, threads=16))
    ILO.solve(pulp.PULP_CBC_CMD(msg=True))


    print(f"Solver Status: {pulp.LpStatus[ILO.status]}")

    print("\nStudent assignments:")
    for s in students:
        for t in teachers:
            if pulp.value(x[s][t]) == 1:
                print(f"  {s} → {t}")

    # Optional: Print pairings that fulfilled preferences
    print("\nMatched preferences (student pairs with 1-sided preference):")
    for s1 in students:
        for s2 in students:
            if s1 != s2 and pulp.value(y[s1][s2]) == 1 and preference_matrix[student_index[s1]][student_index[s2]] == 1:
                print(f"  {s1} ↔ {s2}")

    print("\nAll variable values:")
    for v in ILO.variables():
        print(f"{v.name}: {v.varValue}")


def run_milp():
    school = 'school_2'
    processed_data_folder = 'data/processed_data'
    deviation = 0.3
    min_prefs_per_student = 0

    ILO, x, y, y_group = create_model(school, processed_data_folder, deviation, min_prefs_per_student)
    solve_model(ILO, x, y, y_group, school, processed_data_folder)








