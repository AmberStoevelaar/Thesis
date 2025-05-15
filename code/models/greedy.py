import pandas as pd
import os
from datetime import datetime
import random
from help_functions import create_preference_matrix, read_dfs, read_variables, is_assigned, get_group

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


def get_assigned_students(groups):
    assigned = []
    for students in groups.values():
        assigned.extend(students)
    return assigned

def violates_constraints(student, group, groups, data, variables):
    if violates_max_group_size(group, groups, variables.max_group_size):
        return True
    if violates_min_group_size(group, groups, variables.min_group_size):
        return True
    if violates_binary(student, group, groups, data.info_students, 'Extra Care', variables.max_extra_care):
        return True
    if violates_student_pair(student, group, groups, data.constraints_students, get_assigned_students(groups)):
        return True
    if violates_teacher_pair(student, group, data.constraints_teachers):
        return True

    return False


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


# def greedy_grouping(students, teachers, data, variables, preferences):
#     groups = {teacher: [] for teacher in teachers}

#     # Sort students - e.g. by preference sum ascending or descending
#     students.sort(key=lambda s: preferences.loc[s].sum(), reverse=False)

#     for student in students:
#         best_teacher = None
#         best_score = -1

#         for teacher in teachers:
#             group = groups[teacher]
#             if violates_constraints(student, teacher, groups, data, variables):
#                 continue

#             score = group_preference_score(group, student, preferences)
#             if score > best_score:
#                 best_teacher = teacher
#                 best_score = score

#         if best_teacher is not None:
#             groups[best_teacher].append(student)
#         else:
#             print(f"Warning: No valid group found for student {student}.")

#     return groups

def greedy_grouping(students, teachers, data, variables, preferences, max_attempts=10):
    for attempt in range(max_attempts):
        print(f"Attempt {attempt+1}")

        groups = {teacher: [] for teacher in teachers}
        groups = assign_includes(groups, data)

        assigned_students = {student for group in groups.values() for student in group}
        remaining_students = [s for s in students if s not in assigned_students]

        # Shuffle remaining students to change order each attempt
        random.shuffle(remaining_students)

        success = True

        for student in remaining_students:
            best_teacher = None
            best_score = -1

            for teacher in teachers:
                if violates_constraints(student, teacher, groups, data, variables):
                    continue

                score = group_preference_score(groups[teacher], student, preferences)
                if score > best_score:
                    best_teacher = teacher
                    best_score = score

            if best_teacher is not None:
                groups[best_teacher].append(student)
            else:
                print(f"Warning: No valid group found for student {student}.")
                success = False
                break  # stop early this attempt

        if success:
            return groups

    print("Failed to find a valid grouping after multiple attempts.")
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

    # Run the greedy grouping algorithm
    groups = greedy_grouping(students, teachers, data, variables, preference_matrix)

    # Save the results
    save_results(groups, results_folder, timestamp)

