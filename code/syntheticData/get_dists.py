import os
import pandas as pd

def get_school_paths(folder):
    all_schools = []
    for school in os.listdir(folder):
        if school in skip_schools:
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
        # Get Include density (number of together constraints out of total possible pairs)
        num_students = len(get_df(school, 'info_students.csv'))
        total_possible_student_pairs = num_students * (num_students - 1) // 2

        # Load student data from each school
        df = get_df(school, 'constraints_students.csv')

        # Get number of peer inclusion and exclusion constraints
        peer_incl = (df['Together'] == "Yes").sum()
        peer_excl = (df['Together'] == "No").sum()

        constraints["peer_incl"].append(peer_incl / total_possible_student_pairs)
        constraints["peer_excl"].append(peer_excl / total_possible_student_pairs)

        # Load teacher data from each school
        df = get_df(school, 'constraints_teachers.csv')
        num_teachers = len(df)
        total_possible_teacher_pairs = num_students * num_teachers

        # Get number of teacher inclusion and exclusion constraints
        teacher_incl = (df['Together'] == "Yes").sum()
        teacher_excl = (df['Together'] == "No").sum()

        constraints["teacher_incl"].append(
            teacher_incl / total_possible_teacher_pairs if total_possible_teacher_pairs else 0)
        constraints["teacher_excl"].append(
            teacher_excl / total_possible_teacher_pairs if total_possible_teacher_pairs else 0)

    return constraints

def get_group_info(schools):
    group_info = {"min_group_size": [], "max_extra_care": []}

    for school in schools:
        # Load group data from each school
        df = get_df(school, 'group_preferences.csv')

        # Get minimum group size
        group_info["min_group_size"].append(df.iloc[0]['Minimum Group Size'])

        # Get maximum number of students with extra care in a group
        group_info["max_extra_care"].append(df.iloc[0]["Maximum Number Extra Care"])

    return group_info

def get_all_parameters(schools):
    parameters = {}

    student_info = get_student_info(schools)
    constraints = get_constraints(schools)
    group_info = get_group_info(schools)

    parameters.update(student_info)
    parameters.update(constraints)
    parameters.update(group_info)

    print(parameters)
    return parameters

if __name__ == "__main__":
    folder = 'data/processed_data'

    skip_schools = ["school_1", "school_2", "school_3", "school_4", "school_5", "test_school", ".DS_Store"]
    schools = get_school_paths(folder)

    parameters = get_all_parameters(schools)

