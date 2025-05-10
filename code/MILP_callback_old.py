from pyscipopt import Model
from pyscipopt import quicksum
from pyscipopt import Eventhdlr, SCIP_EVENTTYPE
import numpy as np
import pandas as pd
import time
import csv
import os
import math
from datetime import datetime
from help_functions import create_preference_matrix, read_dfs, read_variables

def create_variables(model, students, teachers):
    x = {}
    y = {}
    y_group = {}

    # Add binary variables for student-teacher assignments (x)
    for s in students:
        for t in teachers:
            x[s, t] = model.addVar(vtype="BINARY", name=f"x_{s}_{t}")

    # Add binary variables for student pairs (y)
    for s1 in students:
        for s2 in students:
            if s1 != s2:
                y[s1, s2] = model.addVar(vtype="BINARY", name=f"y_{s1}_{s2}")
                for t in teachers:
                        y_group[s1, s2, t] = model.addVar(vtype="BINARY", name=f"y_group_{s1}_{s2}_{t}")

    return model, x


def add_preference_objective(model, y, students, preference_matrix):
    satisfied = {}
    min_satisfied = model.addVar(vtype="INTEGER", name="min_satisfied")

    total_expr = 0

    for s1 in students:
        expr = quicksum(
            y[s1, s2] for s2 in students
            if s2 != s1 and preference_matrix.loc[s1, s2] == 1
        )
        satisfied[s1] = expr
        model.addCons(expr >= min_satisfied, name=f"min_satisfied_{s1}")
        total_expr += expr

    return min_satisfied, total_expr


def create_initial_model(students, teachers, data, preferences):
    model = Model("milp")
    model, x, y, y_group = create_variables(model, students, teachers)

    min_satisfied, total_expr = add_preference_objective(model, y, students, preferences)

    # Define weights
    min_weight = 1.0
    total_weight = 1.0

    total_objective = total_weight * total_expr + min_weight * min_satisfied
    model.setObjective(total_objective, sense="maximize")

    return model, x, y, y_group


def add_assignment_constraints(model, x, y, data):
    exclusions_students = data.constraints_students[data.constraints_students['Together'] == 'No'][['Student 1', 'Student 2']].values.tolist()
    exclusions_teacher = data.constraints_teachers[data.constraints_teachers['Together'] == 'No'][['Student', 'Teacher']].values.tolist()
    inclusions_students = data.constraints_students[data.constraints_students['Together'] == 'Yes'][['Student 1', 'Student 2']].values.tolist()
    inclusions_teacher = data.constraints_teachers[data.constraints_teachers['Together'] == 'Yes'][['Student', 'Teacher']].values.tolist()

    # Exclusions between students
    for s1, s2 in exclusions_students:
        model.addCons(y[s1, s2] == 0, name=f"exclusion_{s1}_{s2}")

    # Exclusions between students and teachers
    for s, t in exclusions_teacher:
        model.addCons(x[s, t] == 0, name=f"exclusion_{s}_{t}")

    # Inclusions between students
    for s1, s2 in inclusions_students:
        model.addCons(y[s1, s2] == 1, name=f"inclusion_{s1}_{s2}")

    # Inclusions between students and teachers
    for s, t in inclusions_teacher:
        model.addCons(x[s, t] == 1, name=f"inclusion_{s}_{t}")

    return model

def add_hard_constraints(model, x, y, y_group, students, teachers, data, variables):
    # Mapping "Extra Care" to values
    extra_care_values = dict(zip(
        data.info_students['Student'],
        data.info_students['Extra Care'].map({'Yes': 1, 'No': 0})
    ))

    for s1 in students:
        # Each student is assigned to exactly one teacher
        model.addCons(quicksum(x[s1, t] for t in teachers) == 1, name=f"Student_{s1}_assigned_once")

        for s2 in students:
            if s1 != s2:
                # Link y with y_group
                model.addCons(y[s1, s2] == quicksum(y_group[s1, s2, t] for t in teachers), name=f"set_y_{s1}_{s2}")

                for t in teachers:
                    # Set y_group via implications (using quicksum for summing)
                    model.addCons(
                        y_group[s1, s2, t] <= 0.5 * (x[s1, t] + x[s2, t]),
                        name=f"prop_1_y_group_{s1}_{s2}_{t}"
                    )
                    model.addCons(
                        y_group[s1, s2, t] >= x[s1, t] + x[s2, t] - 1,
                        name=f"prop_2_y_group_{s1}_{s2}_{t}"
                    )

    for t in teachers:
        # Group size constraints
        model.addCons(quicksum(x[s, t] for s in students) >= variables.min_group_size, name=f"Teacher_{t}_min_size")
        model.addCons(quicksum(x[s, t] for s in students) <= variables.max_group_size, name=f"Teacher_{t}_max_size")

        # Max students with extra care
        model.addCons(
            quicksum(x[s, t] * extra_care_values[s] for s in students) <= variables.max_extra_care,
            name=f"max_extra_care_{t}"
        )

    return model

def add_balancing_constraints(model, x, students, teachers, data, attribute, deviation=0.1):
    categories = data.info_students[attribute].unique()

    # Map from category to list of students
    category_students = {
        cat: [s for s in students if data.info_students.loc[data.info_students['Student'] == s, attribute].iloc[0] == cat]
        for cat in categories
    }

    # Compute ideal distribution per teacher
    target_per_teacher = {
        cat: len(category_students[cat]) / len(teachers)
        for cat in categories
    }

    for t in teachers:
        for cat in categories:
            students_in_cat = category_students[cat]
            lower_bound = math.floor((1 - deviation) * target_per_teacher[cat])
            upper_bound = math.ceil((1 + deviation) * target_per_teacher[cat])

            # Add min constraint (using quicksum)
            model.addCons(
                quicksum(x[s, t] for s in students_in_cat) >= lower_bound,
                name=f"{attribute}_{cat}_{t}_min"
            )

            # Add max constraint (using quicksum)
            model.addCons(
                quicksum(x[s, t] for s in students_in_cat) <= upper_bound,
                name=f"{attribute}_{cat}_{t}_max"
            )

    return model







def create_model(school, processed_data_folder):
    # Read data
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    preference_matrix = create_preference_matrix(data, variables)

    model, x, y, y_group = create_initial_model(students, teachers, data, preference_matrix)

    # Hard constraints
    model = add_hard_constraints(model, x, y, y_group, students, teachers, data, variables)
    model = add_assignment_constraints(model, x, y, data)

    # Balancing constraints
    model = add_balancing_constraints(model, x, students, teachers, data, attribute='Gender', deviation=0.1)
    model = add_balancing_constraints(model, x, students, teachers, data, attribute='Grade', deviation=0.1)
    model = add_balancing_constraints(model, x, students, teachers, data, attribute='Extra Care', deviation=0.1)

    return model, x, y, y_group







class MILPObjectiveLogger:
    def __init__(self, results_folder, timestamp):
        self.start_time = time.time()
        self.best_objective = None
        self.solution_count = 0
        self.results_folder = results_folder
        self.timestamp = timestamp

        # Setup paths
        log_folder = os.path.join(results_folder, "logs")
        os.makedirs(log_folder, exist_ok=True)
        self.log_file_path = os.path.join(log_folder, f"ILP_{self.timestamp}.csv")

        # Write header
        with open(self.log_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Solution #", "Elapsed Time (s)", "Objective Value"])

    def log_solution(self, model):
        current_objective = model.getObjVal()
        elapsed = time.time() - self.start_time
        self.solution_count += 1

        if self.best_objective is None or current_objective >= self.best_objective:
            self.best_objective = current_objective
            print(f"[{elapsed:.1f}s] New best solution #{self.solution_count}, objective = {current_objective}")
            self.save_to_csv(elapsed, current_objective)

    def save_to_csv(self, elapsed, current_objective):
        timestamp = datetime.now().strftime("%d-%m_%H:%M:%S")
        with open(self.log_file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, self.solution_count, round(elapsed, 3), current_objective])

    def end_search(self, status_str):
        elapsed = time.time() - self.start_time
        if self.best_objective is not None:
            print(f"[{elapsed:.1f}s] Search ended. Best solution #{self.solution_count}, objective = {self.best_objective}")
            self.save_to_csv(elapsed, self.best_objective)

            # Write final status to logging
            with open(self.log_file_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Status", status_str])

class BestSolutionLogger(Eventhdlr):
    def __init__(self, logger):
        self.logger = logger

    def eventinit(self):
        # Catch events when a new best solution is found
        self.model.catchEvent(SCIP_EVENTTYPE.BESTSOLFOUND, self)

    def eventexit(self):
        self.model.dropEvent(SCIP_EVENTTYPE.BESTSOLFOUND, self)

    def eventexec(self, event):
        self.logger.log_solution(self.model)
        return {"result": None}

def solve_model(model, results_folder, timestamp, timelimit):
    logger = MILPObjectiveLogger(results_folder, timestamp)
    model.setParam("limits/time", timelimit)

    # Register solution logger event handler
    model.includeEventhdlr(BestSolutionLogger(logger), "BestSolutionLogger", "Logs when a better solution is found")

    # Start optimization
    model.optimize()

    # Final log at the end
    logger.end_search(status_str=model.getStatus())

    status_str = model.getStatus()
    if model.getNSols() > 0:
        best_objective = model.getObjVal()
    else:
        best_objective = None
    return best_objective, status_str

def save_solution(model, x, results_folder, timestamp, best_objective, start_time):
    elapsed_time = time.time() - start_time
    output_file = os.path.join(results_folder, f"ILP_{timestamp}.csv")

    assignments = []
    for (s, t), var in x.items():
        val = model.getVal(var)
        print(f"Variable: {var.name}, Value: {val}")
        if val > 0.5:
            assignments.append((s, t))

    df = pd.DataFrame(assignments, columns=["Student", "Teacher"])
    df = df.sort_values(by="Teacher")
    df.to_csv(output_file, index=False)

    print(f"Solution saved to: {output_file}")
    print(f"Final objective value: {best_objective}, Time taken: {elapsed_time:.2f} seconds")


def run_milp(school, processed_data_folder, timelimit):
    # Create model
    model, x, y, y_group = create_model(school, processed_data_folder)

    # Define paths
    results_folder = 'data/results'
    timestamp = datetime.now().strftime("%d-%m_%H:%M")
    os.makedirs(os.path.join(results_folder, school), exist_ok=True)

    # Solve model
    start_time = time.time()
    best_objective, status_str = solve_model(model, os.path.join(results_folder, school), timestamp, timelimit)

    # Save solution
    save_solution(model, x, os.path.join(results_folder, school), timestamp, best_objective, start_time)
    print(f"Solver Status: {status_str}")

