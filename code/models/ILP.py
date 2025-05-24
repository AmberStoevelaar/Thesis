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

def add_objective(model, students, teachers, x, data, variables):
    preferences = create_preference_matrix(data, variables)
    preference_terms = []

    # Maximize student preferences
    for s1 in students:
        weight = 1 / max(1, preferences.loc[s1].sum())
        for s2 in students:
            if s1 != s2 and preferences.loc[s1, s2] > 0:
                for t in teachers:
                    # Create a helper variable that is 1 if both students are assigned to teacher t
                    both_assigned = model.addVar(vtype="BINARY", name=f"pref_{s1}_{s2}_{t}")
                    model.addCons(both_assigned <= x[s1, t])
                    model.addCons(both_assigned <= x[s2, t])
                    model.addCons(both_assigned >= x[s1, t] + x[s2, t] - 1)
                    preference_terms.append(weight * both_assigned)

    attributes_to_balance = ['Gender', 'Grade', 'Extra Care']
    if 'Behavior' in data.info_students.columns:
        attributes_to_balance.append('Behavior')

    balance_penalty_terms = add_balance(model, x, attributes_to_balance, teachers, data)
    fairness_layers = add_fairness_layers(model, x, students, teachers, preferences)

    fairness_terms = []
    max_k = max((k for k, _ in fairness_layers), default=1)
    for k, met_k in fairness_layers:
        weight = 10 ** (max_k - k)
        fairness_terms.append(weight * met_k)

    # # Weights
    balance_weight = 1000
    fairness_weight = 10

    # Set objective
    model.setObjective(
        quicksum(preference_terms)
        + (fairness_weight * quicksum(fairness_terms))
        - (balance_weight * quicksum(balance_penalty_terms)),
        "maximize"
    )

    return model

def create_initial_model(students, teachers, data, variables):
    model = Model("ilp")

    # Decision variables
    # x[s][t] = 1 if student s assigned to teacher t
    x = {}
    for s in students:
        for t in teachers:
            x[s, t] = model.addVar(vtype="BINARY", name=f"x_{s}_{t}")

    model = add_objective(model, students, teachers, x, data, variables)

    return model, x

# SOFT CONSTRAINTS
def add_balance(model, x, attributes, teachers, data):
    balance_penalty_terms = []
    max_students = len(data.info_students)

    for attribute in attributes:
        # Get unique values for the attribute
        categories = data.info_students[attribute].unique()
        # Get target per teacher for each category
        category_students = {cat: data.info_students[data.info_students[attribute] == cat]['Student'].tolist() for cat in categories}
        target_per_teacher = {cat: len(category_students[cat]) / len(teachers) for cat in categories}

        for t in teachers:
            for cat in categories:
                # Get the list of students in this category
                assigned_count = sum(x[s, t] for s in category_students[cat])
                target = target_per_teacher[cat]

                # Calculate over and under deviation
                # over_dev = model.addVar(vtype="INTEGER", name=f"over_dev_{cat}_{t}")
                # under_dev = model.addVar(vtype="INTEGER", name=f"under_dev_{cat}_{t}")
                over_dev = model.addVar(vtype="INTEGER", lb=0, ub=max_students, name=f"over_dev_{cat}_{t}")
                under_dev = model.addVar(vtype="INTEGER", lb=0, ub=max_students, name=f"under_dev_{cat}_{t}")


                model.addCons(assigned_count - int(target) == over_dev - under_dev)
                balance_penalty_terms.append(over_dev)
                balance_penalty_terms.append(under_dev)

    return balance_penalty_terms

def add_fairness_layers(model, x, students, teachers, preferences):
    all_layer_vars = []

    for s1 in students:
        preferred_students = [s2 for s2 in students if s1 != s2 and preferences.loc[s1, s2] == 1]
        num_prefs = len(preferred_students)

        if num_prefs == 0:
            continue

        satisfied_bools = []
        # Get the preferred students for this student
        for s2 in preferred_students:
            together = model.addVar(vtype="BINARY", name=f"together_{s1}_{s2}")
            model.addCons(together <= quicksum(x[s1, t] * x[s2, t] for t in teachers))
            model.addCons(together >= quicksum(x[s1, t] + x[s2, t] - 1 for t in teachers))
            satisfied_bools.append(together)

        num_satisfied = model.addVar(vtype="INTEGER", lb=0, ub=num_prefs, name=f"satisfied_count_{s1}")
        model.addCons(num_satisfied == quicksum(satisfied_bools))

        for k in range(1, num_prefs + 1):
            met_k = model.addVar(vtype="BINARY", name=f"{s1}_at_least_{k}_prefs")
            model.addCons(num_satisfied >= k - (1 - met_k) * num_prefs)
            model.addCons(num_satisfied <= num_prefs - (1 - met_k))

            all_layer_vars.append((k, met_k))

    return all_layer_vars

# HARD CONSTRAINTS
def add_fairness_constraints(model, x, students, teachers, preferences, min_prefs_per_kid):
    for s1 in students:
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

    return model

def add_balancing_constraints(model, x, students, teachers, data, attribute, deviation):
    categories = data.info_students[attribute].unique()
    category_students = {cat: data.info_students[data.info_students[attribute] == cat]['Student'].tolist() for cat in categories}
    target_per_teacher = {cat: len(category_students[cat]) / len(teachers) for cat in categories}

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

def add_hard_constraints(model, x, students, teachers, data, variables, preferences, min_prefs_per_kid, deviation):
    for s1 in students:
        # Each student is assigned to exactly one teacher
        model.addCons(quicksum(x[s1, t] for t in teachers) == 1, name=f"Student_{s1}_assigned_once")

    # Assignment constraints
    for _, (s1, s2, together) in data.constraints_students.iterrows():
        for t in teachers:
            if together == "Yes":
                # Students must be together
                model.addCons(x[s1, t] == x[s2, t])
            elif together == "No":
                # Students must not be together
                model.addCons(x[s1, t] + x[s2, t] <= 1)

    for _, (s, t, together) in data.constraints_teachers.iterrows():
        if together == "Yes":
            # Student must be with the teacher
            model.addCons(x[s, t] == 1)
        elif together == "No":
            # Student must not be with the teacher
            model.addCons(x[s, t] == 0)

    for t in teachers:
        # Group size constraints
        model.addCons(quicksum(x[s, t] for s in students) >= variables.min_group_size, name=f"Teacher_{t}_min_size")
        model.addCons(quicksum(x[s, t] for s in students) <= variables.max_group_size, name=f"Teacher_{t}_max_size")

        # Max extra care constraints
        extra_care_values = dict(zip(data.info_students['Student'], data.info_students['Extra Care'].map({'Yes': 1, 'No': 0})))
        model.addCons(quicksum(x[s, t] * extra_care_values[s] for s in students) <= variables.max_extra_care,
            name=f"max_extra_care_{t}")

    # Add fairness constraints
    model = add_fairness_constraints(model, x, students, teachers, preferences, min_prefs_per_kid)

    # Balancing constraints
    model = add_balancing_constraints(model, x, students, teachers, data, 'Gender', deviation)
    model = add_balancing_constraints(model, x, students, teachers, data, 'Grade', deviation)
    model = add_balancing_constraints(model, x, students, teachers, data, 'Extra Care', deviation)

    # Add balance constraints for behavior if specified
    if 'Behavior' in data.info_students.columns:
        model = add_balancing_constraints(model, x, students, teachers, data, 'Behavior', deviation)
    else:
        print("No 'Behavior' attribute found in the data. Skipping balancing constraints for behavior.")

    return model


def create_model(school, processed_data_folder, min_prefs_per_kid, deviation):
    # Read data
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    # Initialize model
    model, x = create_initial_model(students, teachers, data, variables)

    # Hard constraints
    preference_matrix = create_preference_matrix(data, variables)
    model = add_hard_constraints(model, x, students, teachers, data, variables, preference_matrix, min_prefs_per_kid, deviation)

    return model, x



class ILPObjectiveLogger:
    def __init__(self, results_folder, timestamp, timelimit, min_prefs_per_kid, deviation):
        self.start_time = time.time()
        self.best_objective = None
        self.solution_count = 0
        self.results_folder = results_folder
        self.timestamp = timestamp
        self.school =  os.path.basename(os.path.dirname(results_folder))

        # Setup paths
        log_folder = os.path.join(results_folder, "logs")
        os.makedirs(log_folder, exist_ok=True)
        self.log_file_path = os.path.join(log_folder, f"ILP_{self.timestamp}.csv")

        # Open the CSV file and write headers if it doesn't exist
        with open(self.log_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Add metadata to the CSV file
            writer.writerow(["Run Config"])
            writer.writerow(["School", self.school])
            writer.writerow(["Method", "CP"])
            writer.writerow(["Min Prefs Per Kid", min_prefs_per_kid])
            writer.writerow(["Deviation", deviation])
            writer.writerow(["Time Limit (s)", timelimit])
            writer.writerow([])
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

def solve_model(model, results_folder, timestamp, timelimit, min_prefs_per_kid, deviation):
    logger = ILPObjectiveLogger(results_folder, timestamp, timelimit, min_prefs_per_kid, deviation)
    model.setParam("limits/time", timelimit)
    model.setParam("parallel/maxnthreads", 1)
    model.setParam("randomization/randomseedshift", 42)
    model.setParam("randomization/permutationseed", 42)
    model.setParam("randomization/permutevars", False)

    # Register solution logger event handler
    model.includeEventhdlr(BestSolutionLogger(logger), "BestSolutionLogger", "Logs when a better solution is found")

    # Start optimization
    model.optimize()

    # Final log at the end
    logger.end_search(status_str=model.getStatus())

    status_str = model.getStatus()
    return status_str

def format_solution(model, x):
    assignments = []
    for (s, t), var in x.items():
        val = model.getVal(var)
        if val > 0.5:
            assignments.append((s, t))

    df = pd.DataFrame(assignments, columns=["Student", "Teacher"])
    df = df.sort_values(by="Teacher")

    return df

def run_ilp(school, processed_data_folder, timelimit, min_prefs_per_kid, deviation):
    folder = 'data/results'
    timestamp = datetime.now().strftime("%d-%m_%H:%M")
    results_folder = os.path.join(folder, school, "ILP")

    fallback_configs = [
        (min_prefs_per_kid, deviation),
        (0, deviation),
        (min_prefs_per_kid, 1.0),
        (0, 1.0),
    ]

    for min_prefs, dev in fallback_configs:
        print(f"New run. Trying: min_prefs_per_kid={min_prefs}, deviation={dev}")
        model, x = create_model(school, processed_data_folder, min_prefs, dev)
        solution = solve_model(model, results_folder, timestamp, timelimit, min_prefs, dev)
        # if solution:
        if model.getNSols() > 0:
            df = format_solution(model, x)
            return df, timestamp

    print("No solution found.")
    return None, timestamp

