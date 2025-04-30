import pandas as pd
import os

def read_df(school, processed_data_folder, filename):
    path = os.path.join(processed_data_folder, school, filename)
    return pd.read_csv(path)

# Student-student constraints have a yes AND a no

# Teacher-student constraints have a yes AND a no

# Student-student hava a yes but student1-teacher student2-teacher are different
# Student-student have a no but student1-teacher student2-teacher are the same

# student-student have a yes but student-1 teacher is yes and student2-teacher is no

# Two student-teacher pairs cannot be not together
# A student has both a "Yes" and a "No" to the same teacher


def validate_teachers(info_teachers, constraints_teachers, current_groups):
    teachers = info_teachers['Teacher'].tolist()
    teachers_in_constraints = set(constraints_teachers['Teacher'])
    teachers_in_groups = set(current_groups['Teacher'])

    all_teachers = teachers_in_constraints | teachers_in_groups
    invalid_teachers = [t for t in all_teachers if t not in teachers]

    return invalid_teachers


def validate_constraint_consistency(constraints_students, constraints_teachers):
    is_valid = True

    # 1. Check if student pairs have a yes and a no
    pair_map = constraints_students.groupby(constraints_students[['Student 1', 'Student 2']].apply(lambda x: tuple(sorted(x)), axis=1))['Together'].nunique()
    conflicts = pair_map[pair_map > 1]
    if not conflicts.empty:
        print(f' Conflicting student pair constraints found: {conflicts}')
        is_valid = False

    # 2. Check if student teacher pairs have a yes and a no
    pair_map = constraints_teachers.groupby(constraints_teachers[['Student', 'Teacher']].apply(lambda x: tuple(sorted(x)), axis=1))['Together'].nunique()
    conflicts = pair_map[pair_map > 1]
    if not conflicts.empty:
        print(f'Conflicting student-teacher constraints found: {conflicts}')
        is_valid = False

    # 3. Check if there are students assigned to multiple teachers
    student_teacher_yes = constraints_teachers[constraints_teachers['Together'].str.lower() == 'yes']
    teacher_counts = student_teacher_yes.groupby('Student')['Teacher'].nunique()
    multi_teacher_students = teacher_counts[teacher_counts > 1]

    if not multi_teacher_students.empty:
        print(f'Students assigned to multiple teachers: {multi_teacher_students}')
        is_valid = False

    # 4. Check for student pair and teacher assignment conflicts
    teacher_map = student_teacher_yes.groupby('Student')['Teacher'].apply(set).to_dict()
    for _, (s1, s2, together) in constraints_students.iterrows():
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



def validate_grouping_data(school, processed_data_folder, n_students, n_groups, min_group_size, max_extra_care):
    # TODO: add validation if constraints are in conflict with each other


    info_students = read_df(school, processed_data_folder, 'info_students.csv')
    info_teachers = read_df(school, processed_data_folder, 'info_teachers.csv')
    constraints_students = read_df(school, processed_data_folder, 'constraints_students.csv')
    constraints_teachers = read_df(school, processed_data_folder, 'constraints_teachers.csv')
    current_groups = read_df(school, processed_data_folder, 'current_groups.csv')

    n_extra_care = len(info_students[info_students['Extra Care'] == 'Yes'])

    # Check if number of students is equal to the number of students in the info_students df
    if n_students != len(info_students):
        print(f"Error: The number of students in the group preferences ({n_students}) does not match the number of students in the info_students df ({len(info_students)}).")
        return False

    # Check if minimum group size * number of groups does not exceed number of students
    if min_group_size * n_groups > n_students:
        print(f"Error: The minimum group size of {min_group_size} requires {min_group_size * n_groups} students for {n_groups} groups, "
              f"but there are {n_students} students. You need to reduce the minimum group size or number of groups.")
        return False

    # Check if number of teachers is equal to the number of groups
    if len(info_teachers) != n_groups:
        print(f"Error: The number of teachers ({len(info_teachers)}) does not match the number of groups ({n_groups}).")
        return False

    # Check if all appearances of teachers are in the info_teachers df
    invalid_teachers = validate_teachers(info_teachers, constraints_teachers, current_groups)
    if invalid_teachers != []:
        print(f"Warning: The following teachers appear in constraints or groups but not in info_teachers: {invalid_teachers}")
        return False

    # Check if maximum extra care * number of groups is not less than number of students with extra care
    if n_extra_care > max_extra_care * n_groups:
        print(f"Error: The maximum number of extra care students per group is {max_extra_care}, "
              f"but there are {n_extra_care} students with extra care. "
              f"You need to increase the maximum number of extra care students per group or increase the number of groups.")
        return False

    # Check constraint consistency
    invalid_constraints = validate_constraint_consistency(constraints_students, constraints_teachers)
    if invalid_constraints == False:
        print("Error: Constraints are inconsistent.")
        return False


    return True