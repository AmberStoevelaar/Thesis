import os
import pandas as pd
import numpy as np
import math

def get_school_paths(folder, skip_schools):
    all_schools = []
    for school in os.listdir(folder):
        if school in skip_schools or school.startswith("synthetic_school"):
            continue

        all_schools.append(os.path.join(folder, school))
    return all_schools

def get_df(school, filename):
    path = os.path.join(school, filename)
    if not os.path.exists(path):
        print(f"File {filename} not found in {school}. Skipping.")
        return None
    return pd.read_csv(path)

def get_student_info(schools):
    student_info = {"grades": [], "perc_with_prefs": [], "perc_extra_care": [],
                    "avg_prefs": [], "perc_boys": []}

    for school in schools:
        # Load student data from each school
        df = get_df(school, 'info_students.csv')

        # Get unique grades
        grades = len(df['Grade'].unique().tolist())
        student_info["grades"].append(grades)

        # Get percentage of students with extra care
        perc_extra_care = (df["Extra Care"] == "Yes").mean() * 100
        student_info["perc_extra_care"].append(perc_extra_care)

        # Get percentage of boys
        perc_boys = (df["Gender"] == "Boy").mean() * 100
        student_info["perc_boys"].append(perc_boys)

        # Get percentage of students with preferences
        perc_with_prefs = (df["Preference 1"].notna() | df["Preference 2"].notna() |
                           df["Preference 3"].notna() | df["Preference 4"].notna() |
                           df["Preference 5"].notna()).mean() * 100
        student_info["perc_with_prefs"].append(perc_with_prefs)

        # Get average number of preferences per student
        avg_prefs = df[['Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']].notna().sum(axis=1).mean()
        student_info["avg_prefs"].append(avg_prefs)

    return student_info

def get_constraints(schools):
    constraints = {"peer_incl": [], "peer_excl": [], "teacher_incl": [], "teacher_excl": []}

    for school in schools:
        # Load student data from each school
        df = get_df(school, 'constraints_students.csv')

        # Get number of peer inclusion and exclusion constraints
        peer_incl = (df['Together'] == "Yes").sum()
        peer_excl = (df['Together'] == "No").sum()

        constraints["peer_incl"].append(peer_incl)
        constraints["peer_excl"].append(peer_excl)

        # Load teacher data from each school
        df = get_df(school, 'constraints_teachers.csv')
        num_teachers = len(df)

        # Get number of teacher inclusion and exclusion constraints
        teacher_incl = (df['Together'] == "Yes").sum()
        teacher_excl = (df['Together'] == "No").sum()
        constraints["teacher_incl"].append(teacher_incl)
        constraints["teacher_excl"].append(teacher_excl)
    return constraints

def get_min_group_size_ratios(schools):
    ratios = []
    for school in schools:
        students_df = get_df(school, 'info_students.csv')
        groups_df = get_df(school, 'group_preferences.csv')

        if students_df is None or groups_df is None:
            continue

        num_students = len(students_df)
        min_group_size = groups_df.iloc[0]['Minimum Group Size']
        num_groups = groups_df.iloc[0]['Number of Groups']
        print(f"num groups {num_groups}")
        max_group_size = math.ceil(num_students / num_groups)

        ratio = min_group_size / max_group_size
        ratios.append(ratio)
    return ratios

def get_group_info(schools):
    group_info = {"min_group_size_ratio": [], "max_extra_care_ratio": [], "num_groups_ratio": []}

    for school in schools:
        # Load group data from each school
        df = get_df(school, 'group_preferences.csv')
        num_students = df["Number of Students"].iloc[0]

        # Get minimum group size
        min_group_size = df.iloc[0]['Minimum Group Size']
        group_info["min_group_size_ratio"].append(min_group_size / num_students if num_students > 0 else 0)

        # Get maximum number of students with extra care in a group
        max_extra_care = df.iloc[0]['Maximum Number Extra Care']
        info_df = get_df(school, 'info_students.csv')
        num_extra_care_kids = (info_df["Extra Care"] == "Yes").sum()
        group_info["max_extra_care_ratio"].append(max_extra_care / num_extra_care_kids if num_extra_care_kids > 0 else 0)
        # group_info["max_extra_care_ratio"].append(max_extra_care / num_students if num_students > 0 else 0)

        # Get number of groups
        num_groups = df.iloc[0]['Number of Groups']
        group_info["num_groups_ratio"].append(num_groups / num_students if num_students > 0 else 0)

    return group_info

def get_all_parameters(schools):
    parameters = {}

    student_info = get_student_info(schools)
    constraints = get_constraints(schools)
    group_info = get_group_info(schools)

    parameters.update(student_info)
    parameters.update(constraints)
    parameters.update(group_info)

    return parameters

def compute_summary_stats(schools):
    parameters = get_all_parameters(schools)
    summary_stats = {}

    for key, values in parameters.items():
        arr = np.array(values)
        summary_stats[key] = {
            "min": np.min(arr),
            "max": np.max(arr),
            "mean": np.mean(arr)
        }
    return summary_stats
