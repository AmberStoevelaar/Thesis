from ortools.sat.python import cp_model
import math
import os
from datetime import datetime
import pandas as pd
from help_functions import read_df, get_max_group_size, create_preference_matrix

class InputData:
    def __init__(self, group_preferences, info_students, info_teachers, constraints_students, constraints_teachers):
        self.group_preferences = group_preferences
        self.info_students = info_students
        self.info_teachers = info_teachers
        self.constraints_students = constraints_students
        self.constraints_teachers = constraints_teachers

class Groupvariables:
    def __init__(self, n_students, n_groups, min_group_size, max_extra_care, max_group_size):
        self.n_students = n_students
        self.n_groups = n_groups
        self.min_group_size = min_group_size
        self.max_extra_care = max_extra_care
        self.max_group_size = max_group_size

def read_dfs(school, processed_data_folder):
    return InputData(
        read_df(school, processed_data_folder, 'group_preferences.csv'),
        read_df(school, processed_data_folder, 'info_students.csv'),
        read_df(school, processed_data_folder, 'info_teachers.csv'),
        read_df(school, processed_data_folder, 'constraints_students.csv'),
        read_df(school, processed_data_folder, 'constraints_teachers.csv')
    )

def read_variables(data):
    group_preferences = data.group_preferences
    n_students, n_groups, min_group_size, max_extra_care = group_preferences.iloc[0]
    max_group_size = get_max_group_size(min_group_size, n_students, n_groups)
    return Groupvariables(n_students, n_groups, min_group_size, max_extra_care, max_group_size)



def add_objective(model, x, y, students, data, variables):
    preferences = create_preference_matrix(data.info_students, variables.n_students)
    objectives = []

    # Maximize student preferences
    for s1 in students:
        for s2 in students:
            if s1 != s2:
                objectives.append(preferences.loc[s1, s2] * y[s1, s2])

    # TODO: add fairness objective

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
            print(f"Adding balance constraints for {cat} in teacher {t}: [{lower_bound}, {upper_bound}]")

            # Get the list of students in this category
            students_in_cat = category_students[cat]

            # Add the balancing constraints for this category
            model.Add(sum(x[s, t] for s in students_in_cat) >= lower_bound)
            model.Add(sum(x[s, t] for s in students_in_cat) <= upper_bound)

    return model

def add_hard_constraints(model, x, y, y_group, students, teachers, data, variables):
    for s1 in students:
        # Each student must be assigned to exactly one teacher
        # model.Add(sum(x[s1, t] for t in teachers) == 1)
        model.AddExactlyOne(x[s1, t] for t in teachers)

        for s2 in students:
            if s1 != s2:
                # Link y with y_group
                model.AddMaxEquality(y[s1, s2], [y_group[s1, s2, t] for t in teachers])
                # model.Add(y[s1, s2] == sum(y_group[s1, s2, t] for t in teachers))

                for t in teachers:
                    # Set y_group if both students are assigned to the same teacher
                    model.AddBoolAnd([x[s1, t], x[s2, t]]).OnlyEnforceIf(y_group[s1, s2, t])
                    model.AddBoolOr([x[s1, t].Not(), x[s2, t].Not()]).OnlyEnforceIf(y_group[s1, s2, t].Not())



    # Assignment constraints
    for _, (s1, s2, together) in data.constraints_students.iterrows():
        print(f"Adding constraint for students {s1} and {s2}: {together}")

        for t in teachers:
            if together == "Yes":
                # Students must be together
                model.Add(x[s1, t] == x[s2, t])
            elif together == "No":
                # Students must not be together
                model.Add(x[s1, t] + x[s2, t] <= 1)

    for _, (s, t, together) in data.constraints_teachers.iterrows():
        print(f"Adding constraint for student {s} and teacher {t}: {together}")

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
    model = add_balance_constraints(model, 'Gender', 0.1, x, teachers, data)
    model = add_balance_constraints(model, 'Grade', 0.1, x, teachers, data)

    return model


def create_initial_model(students, teachers, data, variables):
    model = cp_model.CpModel()

    # Decision variables
    # x[s][t] = 1 if student s assigned to teacher t
    x = {}
    for s in students:
        for t in teachers:
            x[s, t] = model.NewBoolVar(f'x_{s}_{t}')

    # y[s1][s2] = 1 if students s1 and s2 are together
    y = {}
    for s1 in students:
        for s2 in students:
            if s1 != s2:
                y[s1, s2] = model.NewBoolVar(f'y_{s1}_{s2}')
            else:
                y[s1, s2] = 0

    # y_group[s1][s2][t] = 1 if students s1 and s2 are together with teacher t
    y_group = {}
    for s1 in students:
        for s2 in students:
            if s1 != s2:
                for t in teachers:
                    y_group[s1, s2, t] = model.NewBoolVar(f'y_{s1}_{s2}_{t}')

    model = add_objective(model, x, y, students, data, variables)

    return model, x, y, y_group

def create_model(school, processed_data_folder):
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    # Initialize model
    model, x, y, y_group = create_initial_model(students, teachers, data, variables)

    # Add hard constraints
    model = add_hard_constraints(model, x, y, y_group, students, teachers, data, variables)

    return model, x, y, y_group



def solve_model(model, x, y, y_group):
    # Create a solver and solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    print(f"Status: {solver.StatusName(status)}")

    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        # print(f"x={solver.Value(x)}, y={solver.Value(y)}, y_group={solver.Value(y_group)}")
        print(f'solution: {solver.ObjectiveValue()}')
        # print(f'x={solver.Value(x)}')
        # print({key: solver.Value(var) for key, var in x.items()})
        solution = {key: solver.Value(var) for key, var in x.items()}

        return solution


def save_solution(solution, school):
    assignments = [
        (student, teacher)
        for (student, teacher), assigned in solution.items()
        if assigned == 1
    ]

    df = pd.DataFrame(assignments, columns=['Student', 'Teacher'])
    df = df.sort_values(by='Teacher')

    results_data_folder='data/results'
    base_name = 'CP'
    results_folder = os.path.join(results_data_folder, school)
    if not os.path.exists(results_folder):
        os.makedirs(results_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(results_folder, f"{base_name}_{timestamp}.csv")
    df.to_csv(file_path, index=False)


def run_cp(school, processed_data_folder):
    model, x, y, y_group = create_model(school, processed_data_folder)
    solution = solve_model(model, x, y, y_group)
    save_solution(solution, school)


