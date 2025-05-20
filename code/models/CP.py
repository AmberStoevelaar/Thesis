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
    objectives = []

    # Maximize student preferences
    for s1 in students:
        for s2 in students:
            if s1 != s2 and preferences.loc[s1, s2] > 0:
                for t in teachers:
                    # Create a helper variable that is 1 if both students are assigned to teacher t
                    both_assigned = model.NewBoolVar(f"same_{s1}_{s2}_{t}")
                    model.AddBoolAnd([x[s1, t], x[s2, t]]).OnlyEnforceIf(both_assigned)
                    model.AddBoolOr([x[s1, t].Not(), x[s2, t].Not()]).OnlyEnforceIf(both_assigned.Not())
                    objectives.append(both_assigned)

    # Add the objective to the model
    model.Maximize(sum(objectives))

    return model

def add_balance_constraints(model, attribute, deviation, x, teachers, data):
    categories = data.info_students[attribute].unique()
    category_students = {cat: data.info_students[data.info_students[attribute] == cat]['Student'].tolist() for cat in categories}
    target_per_teacher = {cat: len(category_students[cat]) / len(teachers) for cat in categories}

    for t in teachers:
        for cat in categories:
            lower_bound = math.floor((1 - deviation) * target_per_teacher[cat])
            upper_bound = math.ceil((1 + deviation) * target_per_teacher[cat])
            # print(f"Adding balance constraints for {cat} in teacher {t}: [{lower_bound}, {upper_bound}]")

            # Get the list of students in this category
            students_in_cat = category_students[cat]

            # Add the balancing constraints for this category
            model.Add(sum(x[s, t] for s in students_in_cat) >= lower_bound)
            model.Add(sum(x[s, t] for s in students_in_cat) <= upper_bound)

    return model

def add_hard_constraints(model, x, students, teachers, data, variables, preferences, min_prefs_per_kid, deviation):
    for s1 in students:
        # Each student must be assigned to exactly one teacher
        model.AddExactlyOne(x[s1, t] for t in teachers)

        # Add fairness constraint
        if min_prefs_per_kid > 0:
            preferred_students = [s2 for s2 in students if s1 != s2 and preferences.loc[s1, s2] == 1]

            if preferred_students:
                together_vars = []

                for s2 in preferred_students:
                    # Add the constraint: together = 1 if both students are assigned to the same teacher
                    together = model.NewBoolVar(f"together_{s1}_{s2}")
                    for t in teachers:
                        model.AddImplication(x[s1, t], x[s2, t]).OnlyEnforceIf(together)
                    together_vars.append(together)

                # Require that at least min preferences are satisfied
                model.Add(sum(together_vars) >= min_prefs_per_kid)

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

    # Add balance constraints
    model = add_balance_constraints(model, 'Gender', deviation, x, teachers, data)
    model = add_balance_constraints(model, 'Grade', deviation, x, teachers, data)
    model = add_balance_constraints(model, 'Extra Care', deviation, x, teachers, data)

    # Add balance constraints for behavior if specified
    if 'Behavior' in data.info_students.columns:
        model = add_balance_constraints(model, 'Behavior', deviation, x, teachers, data)
    else:
        print("No 'Behavior' attribute found in the data. Skipping balancing constraints for behavior.")

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

def create_model(school, processed_data_folder, min_prefs_per_kid, deviation):
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    # Initialize model
    model, x = create_initial_model(students, teachers, data, variables)

    # Add hard constraints
    preference_matrix = create_preference_matrix(data, variables)
    model = add_hard_constraints(model, x, students, teachers, data, variables, preference_matrix, min_prefs_per_kid, deviation)

    return model, x




class ObjectiveLogger(cp_model.CpSolverSolutionCallback):
    def __init__(self, results_folder, timestamp, timelimit, min_prefs_per_kid, deviation):
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
        self.file_path = os.path.join(self.results_folder, f"CP_{self.timestamp}.csv")

        # Open the CSV file and write headers if it doesn't exist
        with open(self.file_path, mode='w', newline='') as file:
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




def solve_model(model, x, results_folder, timestamp, timelimit, min_prefs_per_kid, deviation):
    # Create a solver and solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timelimit
    solver.parameters.log_search_progress = True
    solver.parameters.random_seed = 42
    solver.parameters.num_search_workers = 1

    # Set up and attach the logger callback
    logger = ObjectiveLogger(results_folder, timestamp, timelimit, min_prefs_per_kid, deviation)
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


def run_cp(school, processed_data_folder, timelimit, min_prefs_per_kid, deviation):
    model, x, = create_model(school, processed_data_folder, min_prefs_per_kid, deviation)

    folder ='data/results'
    timestamp = datetime.now().strftime("%d-%m_%H:%M")
    results_folder = os.path.join(folder, school, "CP")


    solution = solve_model(model, x, results_folder, timestamp, timelimit, min_prefs_per_kid, deviation)
    if solution:
        print("Solution found!")
    else:
        print("No solution found.")

    df = format_solution(solution)
    return df, timestamp


