import pandas as pd
import random
import os
from datetime import datetime

from copy import deepcopy
from help_functions import read_dfs, read_variables, create_preference_matrix, get_assigned_students, is_assigned, get_group

# Help functions
def violates_max_group_size(group, groups, max_group_size):
    return len(groups[group]) >= max_group_size

def violates_min_group_size(group, groups, min_group_size):
    return len(groups[group]) < min_group_size

def violates_binary(student, group, groups, info_students, col, limit):
    val = info_students.loc[info_students['Student'] == student, col].values[0]
    if val == 'No':
        return False
    count = info_students[info_students['Student'].isin(groups[group]) & (info_students[col] == 'Yes')].shape[0]
    return count >= limit

def violates_student_pair(student, group, groups, constraints_students, assigned_students):
    mask = (constraints_students['Student 1'] == student) | (constraints_students['Student 2'] == student)
    if not mask.any():
        return False

    matches = constraints_students[mask].copy()
    matches['Other'] = matches.apply(lambda row: row['Student 2'] if row['Student 1'] == student else row['Student 1'], axis=1)

    includes = matches[matches['Together'] == 'Yes']['Other'].tolist()
    excludes = matches[matches['Together'] == 'No']['Other'].tolist()

    # Includes must be in the group if assigned
    for inc in includes:
        if inc in assigned_students and inc not in groups[group]:
            return True

    # Excludes must NOT be in the group
    for exc in excludes:
        if exc in assigned_students and exc in groups[group]:
            return True

    return False

def violates_teacher_pair(student, group, constraints_teachers):
    match = constraints_teachers[(constraints_teachers['Student'] == student) & (constraints_teachers['Teacher'] == group)]
    if match.empty:
        return False
    return match['Together'].values[0] == 'No'




# Grouping functions
def assign_includes(groups, data):
    teachers_include = data.constraints_teachers[data.constraints_teachers['Together'] == 'Yes']
    students_include = data.constraints_students[data.constraints_students['Together'] == 'Yes']

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


def group_preference_score(group, student, preferences):
    return sum(preferences.loc[student, peer] for peer in group)

def random_assign_student(groups, unassigned_students, assigned_students, data, variables, preferences):
    for student in unassigned_students:
        group_scores = []

        for group in groups.keys():
            if violates_max_group_size(group, groups, variables.max_group_size):
                continue
            if violates_binary(student, group, groups, data.info_students, 'Extra Care', variables.max_extra_care):
                continue
            if violates_student_pair(student, group, groups, data.constraints_students, assigned_students):
                continue
            if violates_teacher_pair(student, group, data.constraints_teachers):
                continue

            score = group_preference_score(groups[group], student, preferences)
            group_scores.append((group, score))

        # Sort groups by descending preference score
        group_scores.sort(key=lambda x: x[1], reverse=True)

        if group_scores:
            best_group = group_scores[0][0]
            groups[best_group].append(student)
            assigned_students.append(student)
        else:
            print(f"WARNING: Couldn't assign student {student} due to constraints.")

    return groups


# def random_assign_student(groups, unassigned_students, assigned_students, data, variables):
#     for student in unassigned_students:
#         random_groups = list(groups.keys())
#         random.shuffle(random_groups)

#         for group in random_groups:
#             if violates_max_group_size(group, groups, variables.max_group_size):
#                 # print(f"WARNING: Group {group} is already full.")
#                 continue
#             if violates_binary(student, group, groups, data.info_students, 'Extra Care', variables.max_extra_care):
#                 # print(f"WARNING: Group {group} has too many students with Extra Care.")
#                 continue
#             if violates_student_pair(student, group, groups, data.constraints_students, assigned_students):
#                 # print(f"WARNING: Student {student} violates student pair constraints in group {group}.")
#                 continue
#             if violates_teacher_pair(student, group, data.constraints_teachers):
#                 # print(f"WARNING: Student {student} violates teacher pair constraints in group {group}.")
#                 continue

#             groups[group].append(student)
#             assigned_students.append(student)
#             # print(f"Assigned student {student} to group {group}.")
#             break
#         else:
#             print(f"WARNING: Couldn't assign student {student} due to constraints.")

#     return groups


def valid_groups(groups, data, variables):
    assigned_students = get_assigned_students(groups)

    for group in groups:
        if len(groups[group]) < variables.min_group_size or len(groups[group]) > variables.max_group_size:
            print(f"Group {group} violates size constraints.")
            return False

        # Add additional checks for other care columns if needed in the list
        # Check Extra Care limits
        for care_col, limit in [('Extra Care', variables.max_extra_care)]:
            count = data.info_students[data.info_students['Student'].isin(groups[group]) & (data.info_students[care_col] == 'Yes')].shape[0]
            if count > limit:
                print(f' violates max constraint for {care_col} in group {group} with limit {limit}.')
                return False

        # Check student-student constraints
        for student in groups[group]:
            if violates_student_pair(student, group, groups, data.constraints_students,assigned_students):
                print(f"Student {student} violates student pair constraints in group {group}.")
                return False

            if violates_teacher_pair(student, group, data.constraints_teachers):
                print(f"Student {student} violates teacher pair constraints in group {group}.")
                return False

    # Ensure all students assigned
    if len(assigned_students) != len(data.info_students):
        print(f"Not all students assigned. Assigned: {len(assigned_students)}, Total: {len(data.info_students)}")
        return False

    return True


def greedy_grouping(initial_groups, initial_assigned_students, data, variables, preferences, max_attempts=10):
    for i in range(max_attempts):
        groups = deepcopy(initial_groups)
        assigned_students = initial_assigned_students.copy()

        care_students = [s for s in data.info_students[data.info_students['Extra Care'] == 'Yes']['Student'] if s not in assigned_students]
        other_students = [s for s in data.info_students[~(data.info_students['Student'].isin(care_students))]['Student'] if s not in assigned_students]

        random.shuffle(care_students)
        random.shuffle(other_students)
        unassigned_students = care_students + other_students

        # Run one attempt
        groups = random_assign_student(groups, unassigned_students, assigned_students,
                                       data, variables, preferences)

        # Check if groups are valid
        if valid_groups(groups, data, variables):
            print(f'Valid groups found after {i+1} attempts.')
            return groups

    # # If no valid groups found after max attempts, return the last attempt
    print('No valid groups found after maximum attempts.')
    return groups


def save_results(groups, results_folder, timestamp):
    assignments = [(student, teacher) for teacher, students in groups.items() for student in students]

    df = pd.DataFrame(assignments, columns=['Student', 'Teacher'])
    df = df.sort_values(by='Teacher')

    # Save
    file_path = os.path.join(results_folder, f"Greedy_{timestamp}.csv")
    df.to_csv(file_path, index=False)

    # Print the resulting groups
    print("Greedy grouping results:")
    print(df)


def run_greedy(school, processed_data_folder):
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    preference_matrix = create_preference_matrix(data, variables)

    folder ='data/results'
    timestamp = datetime.now().strftime("%d-%m_%H:%M")
    results_folder = os.path.join(folder, school, "Greedy")
    os.makedirs(results_folder, exist_ok=True)

    base_groups = {teacher: [] for teacher in teachers}
    initial_groups = assign_includes(base_groups, data)
    initial_assigned_students = get_assigned_students(initial_groups)

    # Run the greedy grouping algorithm
    # groups = greedy_grouping(students, teachers, data, variables, preference_matrix)
    groups = greedy_grouping(initial_groups, initial_assigned_students, data, variables, preference_matrix)

    # Save the results
    save_results(groups, results_folder, timestamp)

