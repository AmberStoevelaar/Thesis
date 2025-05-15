import os
import csv
from datetime import datetime
import pandas as pd
from help_functions import create_preference_matrix, read_dfs, read_variables

# Helper function to calculate the preference score for a group
def group_preference_score(group, student, preferences):
    return sum(preferences.loc[student, peer] for peer in group)

# def greedy_grouping(students, teachers, variables, preferences):
#     groups = {teacher: [] for teacher in teachers}

#     # Sort students by the number of preferences they have ascending
#     students.sort(key=lambda s: preferences.loc[s].sum(), reverse=False)

#     # Place each student in the best group
#     for student in students:
#         best_teacher = None
#         best_score = -1

#         # Find the best group for student based on preferences
#         for teacher in groups:
#             group = groups[teacher]
#             if len(group) < variables.max_group_size:
#                 score = group_preference_score(group, student, preferences)
#                 if score > best_score:
#                     best_teacher = teacher
#                     best_score = score

#         # Assign student to that group
#         if best_teacher is not None:
#             groups[best_teacher].append(student)

#     return groups

# def process_constraints(data):
#     student_constraints = {(row['Student 1'], row['Student 2']): row['Together']
#                                 for _, row in data.constraints_students.iterrows()}
#     teacher_constraints = {(row['Student'], row['Teacher']): row['Together']
#                            for _, row in data.constraints_teachers.iterrows()}
#     extra_care_students = set(data.info_students[data.info_students["Extra Care"] == "Yes"]['Student'])

#     return student_constraints, teacher_constraints, extra_care_students

def process_constraints(data):
    student_pair_constraints = {}
    for _, row in data.constraints_students.iterrows():
        s1, s2 = row['Student 1'], row['Student 2']
        together = row['Together'] == 'Yes'
        student_pair_constraints[(s1, s2)] = together
        student_pair_constraints[(s2, s1)] = together

    teacher_constraints = {}
    for _, row in data.constraints_teachers.iterrows():
        student, teacher = row['Student'], row['Teacher']
        together = row['Together'] == 'Yes'
        teacher_constraints[(student, teacher)] = together

    extra_care_students = set(data.info_students[data.info_students["Extra Care"].astype(str) == "Yes"]['Student'])

    return student_pair_constraints, teacher_constraints, extra_care_students

def is_valid_assignment(student, group, teacher, student_pair_constraints, teacher_constraints, extra_care_students, variables):
    # Max group size
    if len(group) >= variables.max_group_size:
        return False

    # Teacher-student constraint
    if (student, teacher) in teacher_constraints and teacher_constraints[(student, teacher)] is False:
        return False

    # Student-pair constraints
    for peer in group:
        pair_key_1 = (student, peer)
        pair_key_2 = (peer, student)

        # Check if the pair is forbidden
        if ((pair_key_1 in student_pair_constraints and not student_pair_constraints[pair_key_1]) or
            (pair_key_2 in student_pair_constraints and not student_pair_constraints[pair_key_2])):
            return False

        # Check if the pair is allowed to be together
        if ((pair_key_1 in student_pair_constraints and student_pair_constraints[pair_key_1]) or
            (pair_key_2 in student_pair_constraints and student_pair_constraints[pair_key_2])):
            continue

    # Extra care constraint
    if student in extra_care_students:
        current_extra = sum(1 for s in group if s in extra_care_students)
        if current_extra >= variables.max_extra_care:
            return False

    return True



def greedy_grouping(students, teachers, data, variables, preferences):
    groups = {teacher: [] for teacher in teachers}

    # Preprocess constraints
    student_pair_constraints, teacher_constraints, extra_care_students = process_constraints(data)

    # Sort students by ascending preference sum
    students.sort(key=lambda s: preferences.loc[s].sum(), reverse=False)

    for student in students:
        best_teacher = None
        best_score = -1

        for teacher in groups:
            group = groups[teacher]

            if not is_valid_assignment(student, group, teacher, student_pair_constraints,
                                       teacher_constraints, extra_care_students, variables):
                continue

            score = group_preference_score(group, student, preferences)
            if score > best_score:
                best_teacher = teacher
                best_score = score

        if best_teacher:
            groups[best_teacher].append(student)
        else:
            print(f"Warning: Could not place student {student} due to constraints.")

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




