import pandas as pd
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from help_functions import read_dfs, read_variables

# Student-student constraints have a yes AND a no

# Teacher-student constraints have a yes AND a no

# Student-student hava a yes but student1-teacher student2-teacher are different
# Student-student have a no but student1-teacher student2-teacher are the same

# student-student have a yes but student-1 teacher is yes and student2-teacher is no

# Two student-teacher pairs cannot be not together
# A student has both a "Yes" and a "No" to the same teacher


# def validate_teachers(info_teachers, constraints_teachers, current_groups):
def validate_teachers(data):
    teachers = data.info_teachers['Teacher'].tolist()
    teachers_in_constraints = set(data.constraints_teachers['Teacher'])
    teachers_in_groups = set(data.current_groups['Teacher'])

    all_teachers = teachers_in_constraints | teachers_in_groups
    invalid_teachers = [t for t in all_teachers if t not in teachers]

    return invalid_teachers


def validate_constraint_consistency(data):
    is_valid = True

    # 1. Check if student pairs have a yes and a no
    pair_map = data.constraints_students.groupby(data.constraints_students[['Student 1', 'Student 2']].apply(lambda x: tuple(sorted(x)), axis=1))['Together'].nunique()
    conflicts = pair_map[pair_map > 1]
    if not conflicts.empty:
        print(f' Conflicting student pair constraints found: {conflicts}')
        is_valid = False

    # 2. Check if student teacher pairs have a yes and a no
    pair_map = data.constraints_teachers.groupby(data.constraints_teachers[['Student', 'Teacher']].apply(lambda x: tuple(sorted(x)), axis=1))['Together'].nunique()
    conflicts = pair_map[pair_map > 1]
    if not conflicts.empty:
        print(f'Conflicting student-teacher constraints found: {conflicts}')
        is_valid = False

    # 3. Check if there are students assigned to multiple teachers
    student_teacher_yes = data.constraints_teachers[data.constraints_teachers['Together'].str.lower() == 'yes']
    teacher_counts = student_teacher_yes.groupby('Student')['Teacher'].nunique()
    multi_teacher_students = teacher_counts[teacher_counts > 1]

    if not multi_teacher_students.empty:
        print(f'Students assigned to multiple teachers: {multi_teacher_students}')
        is_valid = False

    # 4. Check for student pair and teacher assignment conflicts
    teacher_map = student_teacher_yes.groupby('Student')['Teacher'].apply(set).to_dict()
    for _, (s1, s2, together) in data.constraints_students.iterrows():
        t1, t2 = teacher_map.get(s1, set()), teacher_map.get(s2, set())

        if together == 'Yes' and t1 and t2 and t1 != t2:
            print(f"{s1} and {s2} must be together but have different teachers: {t1} vs {t2}")
            is_valid = False

    # TODO: Check overige conflicten
    # S1, S2, Yes but S1, T1, Yes and S2, T2, No doesnt work
    # Student pair must be together (Yes) But one has "Yes" to a teacher and the other has "No" to that teacher.
    # S_08,T_02,Yes - S_21,T_02,No - S_08,S_21,Yes
    # EN A must be with B - B must be with C - A must not be with C

    return is_valid



def validate_grouping_data(school, processed_data_folder):
    # TODO: add validation if constraints are in conflict with each other

    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    n_extra_care = len(data.info_students[data.info_students['Extra Care'] == 'Yes'])

    # Check if number of students is equal to the number of students in the info_students df
    if variables.n_students != len(data.info_students):
        print(f"Error: The number of students in the group preferences ({variables.n_students}) does not match the number of students in the info_students df ({len(data.info_students)}).")
        return False

    # Check if minimum group size * number of groups does not exceed number of students
    if variables.min_group_size * variables.n_groups > variables.n_students:
        print(f"Error: The minimum group size of {variables.min_group_size} requires {variables.min_group_size * variables.n_groups} students for {variables.n_groups} groups, "
              f"but there are {variables.n_students} students. You need to reduce the minimum group size or number of groups.")
        return False

    # Check if number of teachers is equal to the number of groups
    if len(data.info_teachers) != variables.n_groups:
        print(f"Error: The number of teachers ({len(data.info_teachers)}) does not match the number of groups ({variables.n_groups}).")
        return False

    # Check if all appearances of teachers are in the info_teachers df
    invalid_teachers = validate_teachers(data)
    if invalid_teachers != []:
        print(f"Warning: The following teachers appear in constraints or groups but not in info_teachers: {invalid_teachers}")
        return False

    # Check if maximum extra care * number of groups is not less than number of students with extra care
    if n_extra_care > variables.max_extra_care * variables.n_groups:
        print(f"Error: The maximum number of extra care students per group is {variables.max_extra_care}, "
              f"but there are {n_extra_care} students with extra care. "
              f"You need to increase the maximum number of extra care students per group or increase the number of groups.")
        return False

    # Check constraint consistency
    invalid_constraints = validate_constraint_consistency(data)
    if invalid_constraints == False:
        print("Error: Constraints are inconsistent.")
        return False


    return True