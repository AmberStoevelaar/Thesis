import pulp
import numpy as np
import pandas as pd
import time
import csv
import os
import math
from datetime import datetime
from help_functions import create_preference_matrix, read_dfs, read_variables

def create_variables(students, teachers):
    x = {s: {t: pulp.LpVariable(f"x_{s}_{t}", cat="Binary") for t in teachers} for s in students}
    y = {s1: {s2: pulp.LpVariable(f'y_{s1}_{s2}', cat='Binary') if s1 != s2 else None for s2 in students} for s1 in students}
    y_group = {s1: {s2: { t: pulp.LpVariable(f"y_{s1}_{s2}_{t}", cat="Binary") for t in teachers}
        for s2 in students if s1 != s2} for s1 in students }
    return x, y, y_group

    # x[s][t] = 1 if student s assigned to teacher t
    # y[s1][s2] = 1 if student s1 and s2 are in the same group (directional)
    # y[s1][s2][t] = 1 if student s1 and s2 are in the same group with teacher t

def create_initial_model(x, y, y_group, students, teachers, data, preferences):
    ILO = pulp.LpProblem("milp", pulp.LpMaximize)

    # Add preference objective
    ILO, satisfied, min_satisfied, prefs_obj, min_prefs_obj = add_student_preference_objective(ILO, y, students, preferences)

    total_objective = prefs_obj + min_prefs_obj
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

def add_balancing_constraints(ILO, x, students, teachers, data, attribute, deviation=0.1):
    categories = data.info_students[attribute].unique()
    category_students = {
        cat: [s for s in students if data.info_students.loc[data.info_students['Student'] == s, attribute].iloc[0] == cat]
        for cat in categories
    }

    target_per_teacher = {
        cat: len(category_students[cat]) / len(teachers)
        for cat in categories
    }

    for t in teachers:
        for cat in categories:
            lower_bound = math.floor((1 - deviation) * target_per_teacher[cat])
            upper_bound = math.ceil((1 + deviation) * target_per_teacher[cat])
            students_in_cat = category_students[cat]

            ILO += pulp.lpSum(x[s][t] for s in students_in_cat) >= lower_bound, f"{attribute}_{cat}_{t}_min"
            ILO += pulp.lpSum(x[s][t] for s in students_in_cat) <= upper_bound, f"{attribute}_{cat}_{t}_max"

    return ILO

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

    ILO = add_balancing_constraints(ILO, x, students, teachers, data, attribute='Gender', deviation=0.1)
    ILO = add_balancing_constraints(ILO, x, students, teachers, data, attribute='Grade', deviation=0.1)
    ILO = add_balancing_constraints(ILO, x, students, teachers, data, attribute='Extra Care', deviation=0.1)

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








