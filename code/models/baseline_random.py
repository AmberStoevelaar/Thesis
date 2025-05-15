import pandas as pd
import random
import os
from datetime import datetime

from copy import deepcopy
from help_functions import read_df, get_assigned_students, is_assigned, get_group, get_max_group_size

# Help functions




# Functions to check violations
def violates_binary(student, group, groups, student_info, col, limit):
    # This function only checks max assignments of a certain binary column
    # - if there are minimum constraints an extra check is needed
    value = student_info.loc[student_info['Student'] == student, col].values[0]
    if value == 'No':
        return False

    # Get number of binary students in the group
    count = student_info[student_info['Student'].isin(groups[group]) & (student_info[col] == 'Yes')].shape[0]

    # Check if the number of binary students in the group exceeds the limit
    if count >= limit:
        return True

    return False


def violates_min_group_size(group, groups, min_group_size):
    # Check if the group size is less than the minimum group size
    if len(groups[group]) < min_group_size:
        return True
    return False


def violates_max_group_size(group, groups, max_group_size):
    if len(groups[group]) >= max_group_size:
        return True
    return False


def violates_student_pair(student, group, groups, constraints_students, assigned_students):
    # Check if student is in constraints
    mask = (constraints_students['Student 1'] == student) | (constraints_students['Student 2'] == student)
    if not mask.any():
        return False

    # Get the other students
    matches = constraints_students[mask].copy()
    matches['Other'] = matches.apply(lambda row: row['Student 2'] if row['Student 1'] == student else row['Student 1'], axis=1)

    includes = matches[matches['Together'] == 'Yes']['Other'].tolist()
    excludes = matches[matches['Together'] != 'Yes']['Other'].tolist()

    # Check if all includes are in the group
    for include in includes:
        if include in assigned_students and include not in groups[group]:
            return True

    # Check if any excludes are in the group
    for exclude in excludes:
        if exclude in assigned_students and exclude in groups[group]:
            return True

    return False


def violates_teacher_pair(student, group, constraints_teachers):
    # Check if student teacher pair is in constraint
    match = constraints_teachers[(constraints_teachers['Student'] == student) & (constraints_teachers['Teacher'] == group)]

    if match.empty:
        return False

    # Check if they are allowed to be together
    if match['Together'].values[0] == 'No':
        return True

    return False


# Grouping functions
def assign_includes(groups, constraints_teachers, constraints_students):
    teachers_include = constraints_teachers[constraints_teachers['Together'] == 'Yes']
    students_include = constraints_students[constraints_students['Together'] == 'Yes']

    # Assign students to teachers based on inclusion constraints
    for _, (student, teacher, _) in teachers_include.iterrows():
        groups[teacher].append(student)

    # Add students that must be together to the same group if already assigned
    for _, (s1, s2, _) in students_include.iterrows():
        if (is_assigned(s1, groups) and is_assigned(s2, groups)) or (not is_assigned(s1, groups) and not is_assigned(s2, groups)):
            # If both students are already assigned or not assigned, do nothing
            continue
        elif is_assigned(s1, groups):
            group = get_group(s1, groups)
            groups[group].append(s2)
        elif is_assigned(s2, groups):
            group = get_group(s2, groups)
            groups[group].append(s1)

    return groups


def random_assign_student(groups, unassigned_students, assigned_students, info_students,  constraints_students, constraints_teachers, max_group_size, max_extra_care):
    for student in unassigned_students:
        random_groups = list(groups.keys())
        random.shuffle(random_groups)

        for group in random_groups:
            if violates_max_group_size(group, groups, max_group_size):
                # print(f"WARNING: Group {group} is already full.")
                continue
            if violates_binary(student, group, groups, info_students, 'Extra Care', max_extra_care):
                # print(f"WARNING: Group {group} has too many students with Extra Care.")
                continue
            if violates_student_pair(student, group, groups, constraints_students, assigned_students):
                # print(f"WARNING: Student {student} violates student pair constraints in group {group}.")
                continue
            if violates_teacher_pair(student, group, constraints_teachers):
                # print(f"WARNING: Student {student} violates teacher pair constraints in group {group}.")
                continue

            groups[group].append(student)
            assigned_students.append(student)
            # print(f"Assigned student {student} to group {group}.")
            break
        else:
            print(f"WARNING: Couldn't assign student {student} due to constraints.")

    return groups


def valid_groups(groups, info_students, constraints_students, constraints_teachers, min_group_size, max_group_size, max_extra_care):
    assigned_students = get_assigned_students(groups)

    for group in groups:
        if len(groups[group]) < min_group_size or len(groups[group]) > max_group_size:
            print(f"Group {group} violates size constraints.")
            return False

        # Add additional checks for other care columns if needed in the list
        # Check Extra Care limits
        for care_col, limit in [('Extra Care', max_extra_care)]:
            count = info_students[info_students['Student'].isin(groups[group]) & (info_students[care_col] == 'Yes')].shape[0]
            if count > limit:
                print(f' violates max constraint for {care_col} in group {group} with limit {limit}.')
                return False

        # Check student-student constraints
        for student in groups[group]:
            if violates_student_pair(student, group, groups, constraints_students,assigned_students):
                print(f"Student {student} violates student pair constraints in group {group}.")
                return False

            if violates_teacher_pair(student, group, constraints_teachers):
                print(f"Student {student} violates teacher pair constraints in group {group}.")
                return False

    # Ensure all students assigned
    if len(assigned_students) != len(info_students):
        print(f"Not all students assigned. Assigned: {len(assigned_students)}, Total: {len(info_students)}")
        return False

    return True


def generate_random_groups(initial_groups, initial_assigned_students, info_students, constraints_students, constraints_teachers, max_group_size, max_extra_care, min_group_size, max_attempts=10):
    for i in range(max_attempts):
        groups = deepcopy(initial_groups)
        assigned_students = initial_assigned_students.copy()

        care_students = [s for s in info_students[info_students['Extra Care'] == 'Yes']['Student'] if s not in assigned_students]
        other_students = [s for s in info_students[~(info_students['Student'].isin(care_students))]['Student'] if s not in assigned_students]

        random.shuffle(care_students)
        random.shuffle(other_students)
        unassigned_students = care_students + other_students

        # Run one attempt
        groups = random_assign_student(groups, unassigned_students, assigned_students,
                                       info_students, constraints_students, constraints_teachers,
                                       max_group_size, max_extra_care)

        # Check if groups are valid
        if valid_groups(groups, info_students, constraints_students, constraints_teachers, min_group_size, max_group_size, max_extra_care):
            print(f'Valid groups found after {i+1} attempts.')
            return groups

    # # If no valid groups found after max attempts, return the last attempt
    print('No valid groups found after maximum attempts.')
    return groups


def save_groups_to_csv(groups, school, results_data_folder='data/results'):
    results_folder = os.path.join(results_data_folder, school)
    if not os.path.exists(results_folder):
        os.makedirs(results_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    solution_folder = os.path.join(results_folder, "solutions")
    os.makedirs(solution_folder, exist_ok=True)

    file_path = os.path.join(solution_folder, f"random_{timestamp}.csv")

    # Convert to DataFrame
    data = []
    for teacher, students in groups.items():
        for student in students:
            data.append({'Student': student, 'Teacher': teacher})

    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    print(f"Saved random groups to {file_path}")




def run_random_baseline(school, processed_data_folder, seed=42):
    # Set random seed for reproducibility
    random.seed(seed)

    group_preferences = read_df(school, processed_data_folder, 'group_preferences.csv')
    info_students = read_df(school, processed_data_folder, 'info_students.csv')
    info_teachers = read_df(school, processed_data_folder, 'info_teachers.csv')
    constraints_students = read_df(school, processed_data_folder, 'constraints_students.csv')
    constraints_teachers = read_df(school, processed_data_folder, 'constraints_teachers.csv')

    n_students, n_groups, min_group_size, max_extra_care = group_preferences.iloc[0]
    max_group_size = get_max_group_size(min_group_size, n_students, n_groups)

    # Initialize groups
    base_groups = {}
    for teacher in info_teachers['Teacher']:
        base_groups[teacher] = []

    # First assign students that only have one option
    initial_groups = assign_includes(base_groups, constraints_teachers, constraints_students)
    initial_assigned_students = get_assigned_students(initial_groups)

    groups = generate_random_groups(initial_groups, initial_assigned_students, info_students, constraints_students, constraints_teachers, max_group_size, max_extra_care, min_group_size)

    # Save the groups to a CSV file
    save_groups_to_csv(groups, school)
