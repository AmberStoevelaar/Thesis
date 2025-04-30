import pulp
import numpy as np
import pandas as pd
import time
import csv
from help_functions import create_preference_matrix, read_dfs, read_variables

def create_variables(students, teachers):
    x = {s: {t: pulp.LpVariable(f"x_{s}_{t}", cat="Binary") for t in teachers} for s in students}
    y = {s1: {s2: pulp.LpVariable(f'y_{s1}_{s2}', cat='Binary') if s1 != s2 else None for s2 in students} for s1 in students}
    # y_group = { (s1, s2, t): pulp.LpVariable(f"y_{s1}_{s2}_{t}", cat="Binary") for s1 in students for s2 in students for t in teachers }
    y_group = {s1: {s2: { t: pulp.LpVariable(f"y_{s1}_{s2}_{t}", cat="Binary") for t in teachers}
        for s2 in students if s1 != s2} for s1 in students }
    return x, y, y_group

    # x[s][t] = 1 if student s assigned to teacher t
    # y[s1][s2] = 1 if student s1 and s2 are in the same group (directional)
    # y[s1][s2][t] = 1 if student s1 and s2 are in the same group with teacher t

def create_initial_model(x, y, y_group, students, teachers, data, preferences):
    ILO = pulp.LpProblem("milp", pulp.LpMaximize)

    # ILO += pulp.lpSum(x.values()), "total_students"
    # ILO += pulp.lpSum(y.values()), "total_pairs"
    # ILO += pulp.lpSum(y_group.values()), "total_groups"

    # Add preference objective
    ILO, satisfied, min_satisfied, prefs_obj, min_prefs_obj = add_student_preference_objective(ILO, y, students, preferences)

    # Add balancing constraints for gender, grade, and extra_care attributes
    ILO, delta_gender, gender_obj = add_balancing_constraints(
        ILO, x, students, teachers, data.info_students, attribute='Gender', weight=1.0
    )

    ILO, delta_grade, grade_obj = add_balancing_constraints(
        ILO, x, students, teachers, data.info_students, attribute='Grade', weight=1.0
    )

    ILO, delta_extra_care, extra_care_obj = add_balancing_constraints(
        ILO, x, students, teachers, data.info_students, attribute='Extra Care', weight=1.0
    )

    total_objective = prefs_obj + min_prefs_obj + gender_obj + grade_obj + extra_care_obj
    ILO += total_objective, "total_objective"

    return ILO


def add_assignment_constraints(ILO, x, y, data):
    exclusions_students = data.constraints_students[data.constraints_students['Together'] == 'No'][['Student 1', 'Student 2']].values.tolist()
    exclusions_teacher = data.constraints_teachers[data.constraints_teachers['Together'] == 'No'][['Student', 'Teacher']].values.tolist()
    inclusions_students = data.constraints_students[data.constraints_students['Together'] == 'Yes'][['Student 1', 'Student 2']].values.tolist()
    inclusions_teacher = data.constraints_teachers[data.constraints_teachers['Together'] == 'Yes'][['Student', 'Teacher']].values.tolist()

    # Exlusions between students
    for s1, s2 in exclusions_students:
        ILO += y[s1][s2] == 0, f'exclusion_{s1}_{s2}'

    # Exclusions between students and teachers
    for s, t in exclusions_teacher:
        ILO += x[s][t] == 0, f'exclusion_{s}_{t}'

    # Inclusions between students
    for s1, s2 in inclusions_students:
        ILO += y[s1][s2] == 1, f'inclusion_{s1}_{s2}'

    # Inclusions between students and teachers
    for s, t in inclusions_teacher:
        ILO += x[s][t] == 1, f'inclusion_{s}_{t}'

    return ILO

def add_hard_constraints(ILO, x, y, y_group, students, teachers, data, variables):
    for s1 in students:
        # Each student is assigned to exactly one teacher
        ILO += pulp.lpSum([x[s1][t] for t in teachers]) == 1, f"Student_{s1}_assigned_once"

        for s2 in students:
            if s1 != s2:
                # Link y with y_group
                ILO += y[s1][s2] == sum([y_group[s1][s2][t] for t in teachers]), f'set_y_{s1}_{s2}'
                # ILO += y[s1][s2] == sum([y_group[s1][s2][t] for t in teachers if y_group[s1][s2][t] is not None]), f'set_y_{s1}_{s2}'

                for t in teachers:
                    # Set y_group
                    ILO += y_group[s1][s2][t] <= (x[s1][t] + x[s2][t]) / 2, f'prop_1_y_group_{s1}_{s2}_{t}'
                    ILO += y_group[s1][s2][t] >= x[s1][t] + x[s2][t] - 1, f'prop_2_y_group_{s1}_{s2}_{t}'

    for t in teachers:
        # Each group has at least min_group_size and at most max_group_size students
        ILO += pulp.lpSum([x[s][t] for s in students]) >= variables.min_group_size, f"Teacher_{t}_min_size"
        ILO += pulp.lpSum([x[s][t] for s in students]) <= variables.max_group_size, f"Teacher_{t}_max_size"

        # Each group has at most max_extra_care students with extra care
        extra_care_values = dict(zip(data.info_students['Student'], data.info_students['Extra Care'].map({'Yes': 1, 'No': 0})))
        ILO += pulp.lpSum([x[s][t] * extra_care_values[s] for s in students]) <= variables.max_extra_care, f"max_extra_care_{t}"

    return ILO

def add_balancing_constraints(ILO, x, students, teachers, data, attribute, weight=1.0):
    # Map students to categories
    categories = data.info_students[attribute].unique()
    category_students = {
        cat: [s for s in students if data.info_students[data.info_students['Student'] == s][attribute].values[0]]
        for cat in categories
    }

    # Calculate the target number of students per teacher for each category
    target_per_teacher = {
        cat: len(category_students[cat]) / len(teachers)
        for cat in categories
    }

    # Create slack variables for the difference between actual and target count
    delta = {
        (t, cat): pulp.LpVariable(f"delta_{attribute}_{t}_{cat}", lowBound=0)
        for t in teachers for cat in categories
    }

    # Add balancing constraints for each teacher and category
    for t in teachers:
        for cat in categories:
            total_in_teacher_group = pulp.lpSum(x[s][t] for s in category_students[cat])
            ILO += total_in_teacher_group - target_per_teacher[cat] <= delta[t, cat], f"balancing_upper_{t}_{cat}"
            ILO += target_per_teacher[cat] - total_in_teacher_group <= delta[t, cat], f"balancing_lower_{t}_{cat}"

    # Add balancing penalty to the objective function
    # ILO += -weight * pulp.lpSum(delta.values()), f"balance_{attribute}_objective"
    objective = -weight * pulp.lpSum(delta.values())

    return ILO, delta, objective

def add_student_preference_objective(ILO, y, students, preference_matrix, min_weight=1.0, total_weight=1.0):
    # Map student names to indices
    # student_idx = {s: i for i, s in enumerate(students)}

    # Track how many preferences each student gets satisfied
    satisfied = {
        s1: pulp.lpSum(y[s1][s2] for s2 in students if preference_matrix.loc[s1, s2] == 1)
        for s1 in students
    }

    # Count how many preferences each student has provided
    num_given_preferences = {
        s1: sum(1 for s2 in students if preference_matrix.loc[s1, s2] == 1)
        for s1 in students
    }

    min_satisfied = pulp.LpVariable("min_student_preferences_satisfied", lowBound=0, cat="Integer")

    for s1 in students:
        ILO += satisfied[s1] <= num_given_preferences[s1], f"max_satisfied_for_{s1}"

    # Add constraint that all students must have at least 'min_satisfied' preferences satisfied
    for s1 in students:
        ILO += satisfied[s1] >= min_satisfied, f"min_satisfaction_for_{s1}"

    # Add to objective
    prefs_obj =  total_weight * pulp.lpSum(satisfied.values())
    min_prefs_obj =  min_weight * min_satisfied

    return ILO, satisfied, min_satisfied, prefs_obj, min_prefs_obj



def create_model(school, processed_data_folder):
    # Read data
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    preference_matrix = create_preference_matrix(data, variables)

    x, y, y_group = create_variables(students, teachers)
    ILO = create_initial_model(x, y, y_group, students, teachers, data, preference_matrix)

    # Hard constraints
    ILO = add_hard_constraints(ILO, x, y, y_group, students, teachers, data, variables)
    ILO = add_assignment_constraints(ILO, x, y, data)

    return ILO

def solve_model(ILO):
    ILO.solve(pulp.PULP_CBC_CMD(msg=True))
    print(f"Solver Status: {pulp.LpStatus[ILO.status]}")


def save_results(ILO, start_time, output_file="solver_results.csv"):
    # Get objective value and CPU time
    status = ILO.status
    objective_value = ILO.objective.value()

    end_time = time.time()
    cpu_time = end_time - start_time

    # Save results to a CSV file
    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Status", "Objective Value", "CPU Time (seconds)"])
        writer.writerow([status, objective_value, cpu_time])

        # Optionally, save the values of all the variables
        writer.writerow(["Variable", "Value"])
        for v in ILO.variables():
            writer.writerow([v.name, v.varValue])

    print(f"Results saved to {output_file}")



def run_milp(school, processed_data_folder):
    ILO = create_model(school, processed_data_folder)
    solve_model(ILO)








