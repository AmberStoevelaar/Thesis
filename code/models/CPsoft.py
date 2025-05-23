from ortools.sat.python import cp_model
import math
import os
import csv
import time
from datetime import datetime
import pandas as pd
from help_functions import create_preference_matrix, read_dfs, read_variables


def add_objective(model, x, students, teachers, data, variables):
    preferences = create_preference_matrix(data, variables)
    preference_terms = []

    # Maximize student preferences
    for s1 in students:
        # Add weight to give more importance to students with less preferences
        weight = 1 / max(1, preferences.loc[s1].sum())
        for s2 in students:
            if s1 != s2 and preferences.loc[s1, s2] > 0:
                for t in teachers:
                    # Create a helper variable that is 1 if both students are assigned to teacher t
                    both_assigned = model.NewBoolVar(f"same_{s1}_{s2}_{t}")
                    model.AddBoolAnd([x[s1, t], x[s2, t]]).OnlyEnforceIf(both_assigned)
                    model.AddBoolOr([x[s1, t].Not(), x[s2, t].Not()]).OnlyEnforceIf(both_assigned.Not())
                    preference_terms.append(weight * both_assigned)

    attributes_to_balance = ['Gender', 'Grade', 'Extra Care']
    if 'Behavior' in data.info_students.columns:
        attributes_to_balance.append('Behavior')

    balance_penalty_terms = add_balance(model, x, attributes_to_balance, teachers, data)
    fairness_layers = add_fairness_layers(model, x, students, teachers, preferences)

    fairness_terms = []
    max_k = max(k for k, _ in fairness_layers) if fairness_layers else 1
    # Exponential weighting (satisfying higher k's matters more)
    for k, met_k in fairness_layers:
        weight = 10 ** (max_k - k)
        fairness_terms.append(weight * met_k)

    # Define objective weights
    balance_weight = 1000
    fairness_weight = 10

    # Add the objective to the model
    model.Maximize(sum(preference_terms)
        + (fairness_weight * sum(fairness_terms))
        -( balance_weight * sum(balance_penalty_terms))
    )

    return model

def create_initial_model(students, teachers, data, variables):
    model = cp_model.CpModel()

    # Decision variables
    # x[s][t] = 1 if student s assigned to teacher t
    x = {}
    for s in students:
        for t in teachers:
            x[s, t] = model.NewBoolVar(f'x_{s}_{t}')

    model = add_objective(model, x, students, teachers, data, variables)

    return model, x

def add_balance(model, x, attributes, teachers, data):
    balance_penalty_terms = []
    max_students = len(data.info_students)

    for attribute in attributes:
        # Get the unique categories for the attribute
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
                over_dev = model.NewIntVar(0, max_students, f"over_dev_{t}_{attribute}_{cat}")
                under_dev = model.NewIntVar(0, max_students, f"under_dev_{t}_{attribute}_{cat}")

                model.Add(assigned_count - int(target) == over_dev - under_dev)
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
            both_assigned = model.NewBoolVar(f"satisfied_{s1}_{s2}")
            both_assigned_per_teacher = [
                model.NewBoolVar(f"{s1}_{s2}_with_{t}") for t in teachers
            ]
            for i, t in enumerate(teachers):
                model.AddBoolAnd([x[s1, t], x[s2, t]]).OnlyEnforceIf(both_assigned_per_teacher[i])
                model.AddBoolOr([x[s1, t].Not(), x[s2, t].Not()]).OnlyEnforceIf(both_assigned_per_teacher[i].Not())

            model.AddBoolOr(both_assigned_per_teacher).OnlyEnforceIf(both_assigned)
            model.AddBoolAnd([v.Not() for v in both_assigned_per_teacher]).OnlyEnforceIf(both_assigned.Not())

            satisfied_bools.append(both_assigned)

        # Count the number of satisfied preferences for this student
        num_satisfied = model.NewIntVar(0, num_prefs, f"num_satisfied_{s1}")
        model.Add(num_satisfied == sum(satisfied_bools))

        # Preference layers: has at least k prefs satisfied?
        for k in range(1, num_prefs + 1):
            met_k = model.NewBoolVar(f"{s1}_at_least_{k}_prefs")
            model.Add(num_satisfied >= k).OnlyEnforceIf(met_k)
            model.Add(num_satisfied < k).OnlyEnforceIf(met_k.Not())
            all_layer_vars.append((k, met_k))

    return all_layer_vars

def add_hard_constraints(model, x, students, teachers, data, variables):
    for s1 in students:
        # Each student must be assigned to exactly one teacher
        model.AddExactlyOne(x[s1, t] for t in teachers)

    # Assignment constraints
    for _, (s1, s2, together) in data.constraints_students.iterrows():
        for t in teachers:
            if together == "Yes":
                # Students must be together
                model.Add(x[s1, t] == x[s2, t])
            elif together == "No":
                # Students must not be together
                model.Add(x[s1, t] + x[s2, t] <= 1)

    for _, (s, t, together) in data.constraints_teachers.iterrows():
        if together == "Yes":
            # Student must be with the teacher
            model.Add(x[s, t] == 1)
        elif together == "No":
            # Student must not be with the teacher
            model.Add(x[s, t] == 0)

    # Maximum group size constraint
    for t in teachers:
        model.Add(sum(x[s, t] for s in students) >= variables.min_group_size)
        model.Add(sum(x[s, t] for s in students) <= variables.max_group_size)

    # Maximum extra care constraints
    extra_care_values = dict(zip(data.info_students['Student'], data.info_students['Extra Care'].map({'Yes': 1, 'No': 0})))
    for t in teachers:
        model.Add(sum(x[s, t] * extra_care_values[s] for s in students) <= variables.max_extra_care)

    return model

def create_model(school, processed_data_folder):
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    # Initialize model
    model, x = create_initial_model(students, teachers, data, variables)

    # Add hard constraints
    model = add_hard_constraints(model, x, students, teachers, data, variables)

    return model, x




class ObjectiveLogger(cp_model.CpSolverSolutionCallback):
    def __init__(self, results_folder, timestamp, timelimit):
        super().__init__()
        self.start_time = time.time()
        self.best_objective = None
        self.solution_count = 0
        self.timestamp = timestamp
        self.school =  os.path.basename(os.path.dirname(results_folder))

        # Create a subfolder for logs
        log_folder = os.path.join(results_folder, "logs")
        os.makedirs(log_folder, exist_ok=True)
        self.results_folder = log_folder

        # Set up the CSV file with a timestamp-based filename
        self.file_path = os.path.join(self.results_folder, f"CPSOFT_{self.timestamp}.csv")

        # Open the CSV file and write headers if it doesn't exist
        with open(self.file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Add metadata to the CSV file
            writer.writerow(["Run Config"])
            writer.writerow(["School", self.school])
            writer.writerow(["Method", "CPSOFT"])
            writer.writerow(["Time Limit (s)", timelimit])
            writer.writerow([])
            writer.writerow(["Timestamp", "Solution #", "Elapsed Time (s)", "Objective Value"])

    def on_solution_callback(self):
        self.solution_count += 1
        current_objective = self.ObjectiveValue()
        elapsed = time.time() - self.start_time

        # Log every new best solution
        if (self.best_objective is None) or (current_objective > self.best_objective):
            self.best_objective = current_objective
            print(f"[{elapsed:.1f}s] New best solution #{self.solution_count}, objective = {current_objective}")
            self.save_to_csv(elapsed, current_objective, self.timestamp)

    def save_to_csv(self, elapsed, current_objective, timestamp):
        with open(self.file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, self.solution_count, round(elapsed, 3), current_objective])

    def EndSearch(self, status_str):
        if self.best_objective is not None:
            elapsed = time.time() - self.start_time
            print(f"[{elapsed:.1f}s] Search ended. Best solution #{self.solution_count}, objective = {self.best_objective}")
            self.save_to_csv(elapsed, self.best_objective, self.timestamp)

            with open(self.file_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Status", status_str])




def solve_model(model, x, results_folder, timestamp, timelimit):
    # Create a solver and solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timelimit
    solver.parameters.log_search_progress = True
    solver.parameters.random_seed = 42
    solver.parameters.num_search_workers = 1

    # Set up and attach the logger callback
    logger = ObjectiveLogger(results_folder, timestamp, timelimit)
    status = solver.SolveWithSolutionCallback(model, logger)
    logger.EndSearch(solver.StatusName(status))

    print(f"Final status: {solver.StatusName(status)}")
    print(f"Final objective reported by solver: {solver.ObjectiveValue()}")

    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        solution = {key: solver.Value(var) for key, var in x.items()}
        return solution


def format_solution(solution):
    assignments = [(student, teacher) for (student, teacher), assigned in solution.items() if assigned == 1]
    df = pd.DataFrame(assignments, columns=['Student', 'Teacher'])
    df = df.sort_values(by='Teacher')
    return df


def run_cp_soft(school, processed_data_folder, timelimit):
    model, x, = create_model(school, processed_data_folder)

    folder ='data/results'
    timestamp = datetime.now().strftime("%d-%m_%H:%M")
    results_folder = os.path.join(folder, school, "CPSOFT")


    solution = solve_model(model, x, results_folder, timestamp, timelimit)

    if solution:
        df = format_solution(solution)
        return df, timestamp
    else:
        print("No solution found.")
        return None, timestamp


