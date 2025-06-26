import os
import csv
import numpy as np
import random
import math
import sys

from distributions import create_dist
from ranges import get_school_paths, compute_summary_stats

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from preprocessing.validate_data import validate_grouping_data

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from helpers import read_variables, read_dfs


def id_format(prefix, i):
    return f"{prefix}_{i:02d}"

def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

def sample_param(stat):
    mean, min_val, max_val = stat['mean'], stat['min'], stat['max']
    dist = create_dist(mean, max_val, min_val)
    return dist.rvs()

def info_students(stats, student_ids, output_path):
    student_rows = []

    grades = int(round(sample_param(stats["grades"])))
    grades_list = list(range(1, grades + 1))
    perc_extra_care = sample_param(stats["perc_extra_care"])
    avg_prefs = sample_param(stats["avg_prefs"])
    perc_boys = sample_param(stats["perc_boys"])
    perc_with_prefs = sample_param(stats["perc_with_prefs"])

    num_with_prefs = int(round((perc_with_prefs / 100) * len(student_ids)))
    students_with_prefs = random.sample(student_ids, k=min(num_with_prefs, len(student_ids)))
    for s in student_ids:
        grade = random.choice(grades_list)
        gender = "Boy" if random.random() < (perc_boys / 100) else "Girl"
        extra_care = "Yes" if random.random() < (perc_extra_care / 100) else "No"

        if s in students_with_prefs:
            # Number of preferences, capped between 0 and 5
            num_prefs = min(5, max(0, int(np.random.normal(loc=avg_prefs, scale=1))))

            # Pick preferences randomly (excluding self)
            possible_prefs = [sid for sid in student_ids if sid != s]
            prefs = random.sample(possible_prefs, k=min(num_prefs, len(possible_prefs)))
        else:
            prefs = []

        # Pad the rest with empty strings so always 5 columns for prefs
        prefs += [""] * (5 - len(prefs))

        row = [s, grade, gender, extra_care] + prefs[:5]
        student_rows.append(row)

    path = os.path.join(output_path, "info_students.csv")
    write_csv(path,
              ["Student", "Grade", "Gender", "Extra Care", "Preference 1", "Preference 2", "Preference 3", "Preference 4", "Preference 5"],
              student_rows)

    num_extra_care = sum(1 for row in student_rows if row[3] == "Yes")
    return num_extra_care

def constraints_students(stats, student_ids, output_path):
    student_constraints = []
    pairs = [(a, b) for i, a in enumerate(student_ids) for b in student_ids[i+1:]]
    random.shuffle(pairs)

    num_peer_incl = int(round(sample_param(stats["peer_incl"])))
    num_peer_excl = int(round(sample_param(stats["peer_excl"])))

    for i in range(num_peer_incl):
        student_constraints.append([pairs[i][0], pairs[i][1], "Yes"])
    for i in range(num_peer_incl, num_peer_incl + num_peer_excl):
        student_constraints.append([pairs[i][0], pairs[i][1], "No"])

    write_csv(os.path.join(output_path, "constraints_students.csv"),
              ["Student 1", "Student 2", "Together"],
              student_constraints)

def constraints_teachers(stats, student_ids, teacher_ids, output_path):
    teacher_constraints = []
    pairs = [(s, t) for s in student_ids for t in teacher_ids]
    random.shuffle(pairs)

    # Real world data does not have many teacher inclusion and exclusion constraints, so we set them to fixed values
    stats["teacher_incl"] = {"mean": 1, "min": 0, "max": 2}
    stats["teacher_excl"] = {"mean": 0.5, "min": 0, "max": 1}
    teacher_incl = int(round(sample_param(stats["teacher_incl"])))
    teacher_excl = int(round(sample_param(stats["teacher_excl"])))

    for i in range(teacher_incl):
        teacher_constraints.append([pairs[i][0], pairs[i][1], "Yes"])
    for i in range(teacher_incl, teacher_incl + teacher_excl):
        teacher_constraints.append([pairs[i][0], pairs[i][1], "No"])

    write_csv(os.path.join(output_path, "constraints_teachers.csv"),
              ["Student", "Teacher", "Together"],
              teacher_constraints)

def group_preferences(num_students, num_groups, student_ids, output_path):
    min_group_size_ratio = sample_param(stats["min_group_size_ratio"])
    min_group_size = math.ceil(num_groups * min_group_size_ratio)

    max_extra_care_ratio = sample_param(stats["max_extra_care_ratio"])
    num_extra_care = info_students(stats, student_ids, output_path)
    max_extra_care = math.ceil(num_extra_care * max_extra_care_ratio)

    group_info = [[num_students, num_groups, min_group_size, max_extra_care]]

    write_csv(os.path.join(output_path, "group_preferences.csv"),
              ["Number of Students", "Number of Groups", "Minimum Group Size", "Maximum Number Extra Care"],
              group_info)

def info_teachers(teacher_ids, output_path):
    write_csv(os.path.join(output_path, "info_teachers.csv"),
              ["Teacher"],
              [[t] for t in teacher_ids])

def current_groups(output_path):
    write_csv(os.path.join(output_path, "current_groups.csv"),
            ["Student", "Teacher"],
            [])

def generate_synthetic_school(stats, num_students, output_path, seed):
    os.makedirs(output_path, exist_ok=True)

    # Set random seeds for reproducibility
    random.seed(seed)
    np.random.seed(seed)

    # Generate students
    student_ids = [id_format("S", i+1) for i in range(num_students)]

    # Generate number of groups
    num_groups_ratio = sample_param(stats["num_groups_ratio"])
    num_groups = math.ceil(num_students * num_groups_ratio)
    print(f"Generating {num_students} students in {num_groups} groups")

    # Generate teacher
    teacher_ids = [id_format("T", i+1) for i in range(num_groups)]

    # info_students.csv
    info_students(stats, student_ids, output_path)

    # constraints_students.csv
    constraints_students(stats, student_ids, output_path)

    # constraints_teachers.csv
    constraints_teachers(stats, student_ids, teacher_ids, output_path)

    # group_preferences.csv
    group_preferences(num_students, num_groups, student_ids, output_path)

    # info_teachers.csv
    info_teachers(teacher_ids, output_path)

    # current_groups.csv
    current_groups(output_path)

if __name__ == "__main__":
    folder = 'data/processed_data'
    skip_schools = ["school_1", "school_2", "school_3", "school_4", "school_5", "test_school", ".DS_Store"]
    schools = get_school_paths(folder, skip_schools=skip_schools)

    stats = compute_summary_stats(schools)
    print("Synthetic generation parameters and their statistics:")
    for param, values in stats.items():
        print(f"{param}: mean={values['mean']:.3f}, min={values['min']}, max={values['max']}")


    num_students = [45, 57, 63, 69, 75, 82, 88, 94, 100]

    base_seed = 21
    for i in num_students:
        # Different seed for each school based on number of students
        seed = base_seed + i
        school = f"synthetic_school_{i}"
        out_path = os.path.join(folder, school)
        generate_synthetic_school(stats, i, output_path=out_path, seed=seed)

        # Validate data
        data = read_dfs(school=school, processed_data_folder="data/processed_data")
        variables = read_variables(data)

        is_valid = validate_grouping_data(data, variables)
        if is_valid == False:
            exit("Grouping data for {} is invalid. Please check the errors above.".format(school))
        else:
            print("Grouping data for {} is valid.".format(school))
