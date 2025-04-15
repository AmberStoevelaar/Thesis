import pandas as pd
import os

from help_functions import read_df


def validate_grouping_data(school, processed_data_folder, n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2):
    # TODO: add validation if constraints are in conflict with each other
    # Check of alle teachers die je tegenkomt op de lijst staan





    info_students = read_df(school, processed_data_folder, 'info_students.csv')
    info_teachers = read_df(school, processed_data_folder, 'info_teachers.csv')

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

    n_extra_care_1 = len(info_students[info_students['Extra Care'] == 'Yes'])
    n_extra_care_2 = len(info_students[info_students['Extra Care 2'] == 'Yes'])

    # Check if maximum extra care 1 * number of groups is not less than number of students with extra care 1
    if n_extra_care_1 > max_extra_care_1 * n_groups:
        print(f"Error: The maximum number of extra care 1 students per group is {max_extra_care_1}, "
              f"but there are {n_extra_care_1} students with extra care 1. "
              f"You need to increase the maximum number of extra care 1 students per group or increase the number of groups.")
        return False

    # Check if maximum extra care 2 * number of groups is not less than number of students with extra care 2
    if n_extra_care_2 > max_extra_care_2 * n_groups:
        print(f"Error: The maximum number of extra care 2 students per group is {max_extra_care_2}, "
              f"but there are {n_extra_care_2} students with extra care 2. "
              f"You need to increase the maximum number of extra care 2 students per group or increase the number of groups.")
        return False

    return True