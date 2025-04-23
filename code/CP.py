from ortools.sat.python import cp_model
from help_functions import read_df, get_max_group_size, create_preference_matrix

class InputData:
    def __init__(self, group_preferences, info_students, info_teachers, constraints_students, constraints_teachers):
        self.group_preferences = group_preferences
        self.info_students = info_students
        self.info_teachers = info_teachers
        self.constraints_students = constraints_students
        self.constraints_teachers = constraints_teachers

class GroupVars:
    def __init__(self, n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2, max_group_size):
        self.n_students = n_students
        self.n_groups = n_groups
        self.min_group_size = min_group_size
        self.max_extra_care_1 = max_extra_care_1
        self.max_extra_care_2 = max_extra_care_2
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
    n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2 = group_preferences.iloc[0]
    max_group_size = get_max_group_size(min_group_size, n_students, n_groups)
    return GroupVars(n_students, n_groups, min_group_size, max_extra_care_1, max_extra_care_2, max_group_size)



def add_objective(model, x, y, students, info_students):
    preferences = create_preference_matrix(info_students, vars.n_students)
    objectives = []

    # TODO CHECKEN
    for s1 in students:
        for s2 in students:
            if s1 != s2:
                objectives.append(preferences[s1, s2] * y[s1, s2])


    # TODO add min prefs

    # Add the objective to the model
    model.Maximize(sum(objectives))

    return model


# TODO constraints concreet maken
def add_hard_constraints(model, x, y, students, teachers, data):
    # Constraints: each student must be assigned to exactly one teacher
    for s in students:
        model.Add(sum(x[s, t] for t in teachers) == 1)

    # Group constraints: if y[s1][s2] = 1, then assign them to the same teacher
    for s1 in students:
        for s2 in students:
            if s1 != s2:
                model.Add(y[s1, s2] == sum(x[s1, t] + x[s2, t] for t in teachers) // 2)

    return model


# TODO: implement assignment constraints
def add_assignment_constraints(model, x, students, teachers):
    # Example of assignment constraint
    for s in students:
        for t in teachers:
            model.Add(x[s, t] == 1).OnlyEnforceIf([x[s, t]])

    return model


def add_balance_constraints(model, data, students, teachers, x):
    # Example of balancing constraint
    categories = data.info_students['Gender'].unique()
    for category in categories:
        for t in teachers:
            model.Add(sum(x[s, t] for s in students if data.info_students.loc[data.info_students['Student'] == s, 'Gender'].iloc[0] == category) >= (1 - 0.1) * len(students) / len(teachers))
            model.Add(sum(x[s, t] for s in students if data.info_students.loc[data.info_students['Student'] == s, 'Gender'].iloc[0] == category) <= (1 + 0.1) * len(students) / len(teachers))

    return model




def create_initial_model(students, teachers, data):
    model = cp_model.CpModel()

    # Decision variables
    x = {}
    for s in students:
        for t in teachers:
            x[s, t] = model.NewBoolVar(f'x_{s}_{t}')

    y = {}
    for s1 in students:
        for s2 in students:
            if s1 != s2:
                y[s1, s2] = model.NewBoolVar(f'y_{s1}_{s2}')

    #TODO: look at more variables

    model = add_objective(model, x, y, students, data.info_students)

    return model, x, y



def create_model():
    data = read_dfs('school_2', 'data/processed_data')
    vars = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    # Initialize model
    model, x, y = create_initial_model(students, teachers)

    # Add hard constraints
    model = add_hard_constraints(model, x, y, students, teachers, data)

    # Add assignment constraints
    model = add_assignment_constraints(model, x, students, teachers)

    # Add balance constraints
    model = add_balance_constraints(model, data, students, teachers, x)

    return model




def solve_model(model, x, y, z):
    # Create a solver and solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.FEASIBLE:
        print(f"x={solver.Value(x)}, y={solver.Value(y)}, z={solver.Value(z)}")

def save_solution():
    pass



def run_cp():
    school = 'school_2'
    processed_data_folder = 'data/processed_data'

    model, x, y, z = create_model()
    solve_model(model, x, y, z)





    for s1 in students:
        for s2 in students:
            if s1 != s2:
                objective_terms.append(preference_matrix[s1, s2] * y[s1, s2])

