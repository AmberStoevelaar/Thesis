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

    # Add binary variables for student-teacher assignments (x)
    for s in students:
        for t in teachers:
            x[s, t] = model.addVar(vtype="BINARY", name=f"x_{s}_{t}")

    return model, x

def add_preference_objective(model, students, teachers, x, preference_matrix):
    # Total prefs is the sum of all satisfied preferences and is used in the objective to maximize
    total_prefs = 0
    for s1 in students:
        # Count the number of satisfied preferences for each student
        prefs = 0
        for s2 in students:
            if s1 != s2 and preference_matrix.loc[s1, s2] == 1:
                # Create a variable to capture if s1 and s2 are together
                together = model.addVar(vtype="BINARY", name=f"pref_{s1}_{s2}")
                model.addCons(together <= quicksum(x[s1, t] * x[s2, t] for t in teachers))
                model.addCons(together >= quicksum(x[s1, t] + x[s2, t] - 1 for t in teachers))

                # If they are together, add to the preference count
                prefs += together

        # Add the preference count to the total prefs
        total_prefs += prefs

    return total_prefs


def create_initial_model(students, teachers, preferences):
    model = Model("milp")
    model, x = create_variables(model, students, teachers)

    total_prefs = add_preference_objective(model, students, teachers, x, preferences)
    model.setObjective(total_prefs, sense="maximize")

    return model, x


def add_assignment_constraints(model, x, data, teachers):
    for _, (s1, s2, together) in data.constraints_students.iterrows():
        print(f"Adding constraint for students {s1} and {s2}: {together}")

        for t in teachers:
            if together == "Yes":
                # Students must be together
                model.addCons(x[s1, t] == x[s2, t])
            elif together == "No":
                # Students must not be together
                model.addCons(x[s1, t] + x[s2, t] <= 1)

    for _, (s, t, together) in data.constraints_teachers.iterrows():
        print(f"Adding constraint for student {s} and teacher {t}: {together}")

        if together == "Yes":
            # Student must be with the teacher
            model.addCons(x[s, t] == 1)
        elif together == "No":
            # Student must not be with the teacher
            model.addCons(x[s, t] == 0)

    return model

def add_hard_constraints(model, x, students, teachers, data, variables, preferences, min_prefs_per_kid):
    # Mapping "Extra Care" to values
    extra_care_values = dict(zip(
        data.info_students['Student'],
        data.info_students['Extra Care'].map({'Yes': 1, 'No': 0})
    ))

    for s1 in students:
        # Each student is assigned to exactly one teacher
        model.addCons(quicksum(x[s1, t] for t in teachers) == 1, name=f"Student_{s1}_assigned_once")

        # Add fairness constraint
        if min_prefs_per_kid > 0:
            preferred_students = [s2 for s2 in students if s1 != s2 and preferences.loc[s1, s2] == 1]
            if preferred_students:
                together_vars = []

                for s2 in preferred_students:
                    # Add the constraint: together = 1 if both students are assigned to the same teacher
                    together = model.addVar(vtype="BINARY", name=f"together_{s1}_{s2}")
                    model.addCons(together <= quicksum(x[s1, t] * x[s2, t] for t in teachers))
                    model.addCons(together >= quicksum(x[s1, t] + x[s2, t] - 1 for t in teachers))
                    together_vars.append(together)

                # Require that at least min preferences are satisfied
                model.addCons(quicksum(together_vars) >= min_prefs_per_kid, name=f"{s1}_at_least_one_pref")

    for t in teachers:
        # Group size constraints
        model.addCons(quicksum(x[s, t] for s in students) >= variables.min_group_size, name=f"Teacher_{t}_min_size")
        model.addCons(quicksum(x[s, t] for s in students) <= variables.max_group_size, name=f"Teacher_{t}_max_size")

        # Max students with extra care
        model.addCons(quicksum(x[s, t] * extra_care_values[s] for s in students) <= variables.max_extra_care,
            name=f"max_extra_care_{t}")

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
            model.addCons(quicksum(x[s, t] for s in students_in_cat) >= lower_bound,
                name=f"{attribute}_{cat}_{t}_min")

            # Add max constraint (using quicksum)
            model.addCons(quicksum(x[s, t] for s in students_in_cat) <= upper_bound,
                name=f"{attribute}_{cat}_{t}_max")

    return model







def create_model(school, processed_data_folder, min_prefs_per_kid):
    # Read data
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    preference_matrix = create_preference_matrix(data, variables)

    model, x = create_initial_model(students, teachers, preference_matrix)

    # Hard constraints
    model = add_hard_constraints(model, x, students, teachers, data, variables, preference_matrix, min_prefs_per_kid)
    model = add_assignment_constraints(model, x, data, teachers)

    # Balancing constraints
    model = add_balancing_constraints(model, x, students, teachers, data, attribute='Gender', deviation=0.1)
    model = add_balancing_constraints(model, x, students, teachers, data, attribute='Grade', deviation=0.1)
    model = add_balancing_constraints(model, x, students, teachers, data, attribute='Extra Care', deviation=0.1)
    # model = add_balancing_constraints(model, x, students, teachers, data, attribute='Behaviour', deviation=0.1)

    return model, x







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
        if model.getNSols() == 0:
            return  # No solution to log

        try:
            current_objective = model.getSolObjVal(model.getBestSol())
        except Exception as e:
            print(f"Warning: Unable to retrieve objective value: {e}")
            return

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


def run_milp(school, processed_data_folder, timelimit, min_prefs_per_kid):
    # Create model
    model, x = create_model(school, processed_data_folder, min_prefs_per_kid)
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

