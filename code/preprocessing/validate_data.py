import pandas as pd
import os
import sys
from collections import defaultdict, deque
import itertools

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from helpers import create_preference_matrix

def validate_teachers(data, teachers):
    teachers_in_constraints = set(data.constraints_teachers['Teacher'])
    invalid_teachers = [t for t in teachers_in_constraints if t not in teachers]
    return invalid_teachers

def validate_students(data, students):
    students_in_constraints = set(data.constraints_students['Student 1']).union(set(data.constraints_students['Student 2']))
    invalid_students = [s for s in students_in_constraints if s not in students]
    return invalid_students

def validate_student_preference(data, variables, students):
    preference_matrix = create_preference_matrix(data, variables)

    for student in students:
        preferences = preference_matrix.loc[student]
        preferences = preferences[preferences == 1].index.tolist()

        if len(preferences) != len(set(preferences)):
            print(f"Error: {student} has duplicate preferences.")
            return False
        if student in preferences:
            print(f"Error: {student} has themselves as a preference.")
            return False
    return True


def build_together_groups(data):
    graph = defaultdict(set)

    # Filter to only "Yes"
    for _, row in data.constraints_students[data.constraints_students["Together"] == "Yes"].iterrows():
        a, b = row["Student 1"], row["Student 2"]
        graph[a].add(b)
        graph[b].add(a)

    visited, groups = set(), []
    for student in graph:
        if student in visited:
            continue
        queue = deque([student])
        group = set()
        while queue:
            curr = queue.popleft()
            if curr in visited:
                continue
            visited.add(curr)
            group.add(curr)
            queue.extend(graph[curr] - visited)
        groups.append(group)

    return groups

def can_separate(graph, n_groups):
    color = {}

    def is_valid(student, c):
        return all(color.get(neigh) != c for neigh in graph[student])

    def backtrack(students, idx):
        if idx == len(students):
            return True
        student = students[idx]
        for c in range(n_groups):
            if is_valid(student, c):
                color[student] = c
                if backtrack(students, idx + 1):
                    return True
                del color[student]
        return False

    students = list(graph.keys())
    success = backtrack(students, 0)
    if success:
        return True, None
    else:
        return False, set(students)



def check_conflicting_constraints(data, groups):
    conflicts = []
    for _, (s1, s2, together) in data.constraints_students.iterrows():
        teacher1 = data.constraints_teachers[(data.constraints_teachers['Student'] == s1)]
        teacher2 = data.constraints_teachers[(data.constraints_teachers['Student'] == s2)]

        if together == "Yes":
            conflict1 = data.constraints_students[
                ((data.constraints_students['Student 1'] == s1) & (data.constraints_students['Student 2'] == s2) & (data.constraints_students['Together'] == "No"))]
            conflict2 = data.constraints_students[
                ((data.constraints_students['Student 1'] == s2) & (data.constraints_students['Student 2'] == s1) & (data.constraints_students['Together'] == "No"))]

            # Check if there isnt another constraint with No for same students
            if not conflict1.empty or not conflict2.empty:
                conflicts.append((s1, s2, "Duplicate constraints"))

            # Check if there is a conflict with the teacher
            if not teacher1.empty and not teacher2.empty:
                if teacher1['Teacher'].values[0] != teacher2['Teacher'].values[0] and teacher1['Together'].values[0] == 'Yes' and teacher2['Together'].values[0] == 'Yes':
                    conflicts.append((s1, s2, "Conflicting teachers"))

                if teacher1['Teacher'].values[0] == teacher2['Teacher'].values[0] and teacher1['Together'].values[0] != teacher2['Together'].values[0]:
                    conflicts.append((s1, s2, "Conflicting teachers"))

        elif together == "No":
            conflict1 = data.constraints_students[
                ((data.constraints_students['Student 1'] == s1) & (data.constraints_students['Student 2'] == s2) & (data.constraints_students['Together'] == "Yes"))]
            conflict2 = data.constraints_students[
                ((data.constraints_students['Student 1'] == s2) & (data.constraints_students['Student 2'] == s1) & (data.constraints_students['Together'] == "Yes"))]

            # Check if there is another constraint with Yes for same students
            if not conflict1.empty or not conflict2.empty:
                conflicts.append((s1, s2, "Duplicate constraints"))

    all_required_pairs = {}
    for idx, group in enumerate(groups):
        pairs = list(itertools.combinations(group, 2))
        all_required_pairs[f"Group_{idx + 1}"] = pairs

    no_constraints = set(
        tuple(sorted((row['Student 1'], row['Student 2'])))
        for _, row in data.constraints_students.iterrows()
        if row['Together'] == 'No'
    )

    # Check if all pairs in a group have the same teacher
    for group in all_required_pairs.values():
        for (s1, s2) in group:
            if tuple(sorted((s1, s2))) in no_constraints:
                conflicts.append((s1, s2, "Conflicting constraints: transitivity"))

            teacher1 = data.constraints_teachers[(data.constraints_teachers['Student'] == s1)]
            teacher2 = data.constraints_teachers[(data.constraints_teachers['Student'] == s2)]

            if not teacher1.empty and not teacher2.empty:
                if teacher1['Together'].values[0] != teacher2['Together'].values[0]:
                    conflicts.append((s1, s2, "Conflicting teachers"))

    if conflicts:
        print(f"Conflicting constraints found: {conflicts}")
        return False
    return True

def validate_constraints(data, variables):
    groups = build_together_groups(data)

    for group in groups:
        # 1. Check if a group has more students than the allowed max group size
        if len(group) > variables.max_group_size:
            print(f"Error: Due to the required constraints, a group contains more than the maximum allowed group size ({variables.max_group_size}).")
            return False

        # 2. Check if a group has more extra care students than the allowed max extra care students
        extra_care_count = sum([data.info_students.loc[data.info_students['Student'] == student, 'Extra Care'].values[0] == "Yes" for student in group])
        if extra_care_count > variables.max_extra_care:
            print(f"Error: Due to the required constraints, a group contains more than the maximum allowed extra care students ({variables.max_extra_care_students}).")
            return False

    # Check if there are conflicting constraints
    if not check_conflicting_constraints(data, groups):
        return False

    # Check if a student is assigned to multiple teachers
    student_teacher_yes = data.constraints_teachers[data.constraints_teachers['Together'] == 'Yes']
    teacher_counts = student_teacher_yes.groupby('Student')['Teacher'].nunique()
    multi_teacher_students = teacher_counts[teacher_counts > 1]

    if not multi_teacher_students.empty:
        print(f'Students assigned to multiple teachers: {multi_teacher_students}')
        return False

    # Check if a student has both a "Yes" and a "No" to the same teacher
    pair_map = data.constraints_teachers.groupby(data.constraints_teachers[['Student', 'Teacher']].apply(lambda x: tuple(sorted(x)), axis=1))['Together'].nunique()
    conflicts = pair_map[pair_map > 1]
    if not conflicts.empty:
        print(f'Conflicting student-teacher constraints found: {conflicts}')
        return False

    # Check if the 'Together = No' graph can be separated into the given number of groups
    no_graph = defaultdict(set)
    for _, row in data.constraints_students.iterrows():
        if row['Together'] == 'No':
            s1, s2 = row['Student 1'], row['Student 2']
            no_graph[s1].add(s2)
            no_graph[s2].add(s1)

    can_sep, problem_group = can_separate(no_graph, variables.n_groups)
    if not can_sep:
        print(f"Error: The following students are mutually constrained to not be together, "
              f"but cannot be split into {variables.n_groups} groups: {sorted(problem_group)}")
        return False

    return True


def validate_grouping_data(dfs, variables):
    students = dfs.info_students['Student'].tolist()
    teachers = dfs.info_teachers['Teacher'].tolist()

    n_extra_care = len(dfs.info_students[dfs.info_students['Extra Care'] == 'Yes'])

    # Check if number of students is equal to the number of students in the info_students df
    if variables.n_students != len(dfs.info_students):
        print(f"Error: The number of students in the group preferences ({variables.n_students}) does not match the number of students in the info_students df ({len(dfs.info_students)}).")
        return False

    # Check if minimum group size * number of groups does not exceed number of students
    if variables.min_group_size * variables.n_groups > variables.n_students:
        print(f"Error: The minimum group size of {variables.min_group_size} requires {variables.min_group_size * variables.n_groups} students for {variables.n_groups} groups, "
              f"but there are {variables.n_students} students. You need to reduce the minimum group size or number of groups.")
        return False

    # Check if number of teachers is equal to the number of groups
    if len(dfs.info_teachers) != variables.n_groups:
        print(f"Error: The number of teachers ({len(dfs.info_teachers)}) does not match the number of groups ({variables.n_groups}).")
        return False

    # Check if all appearances of teachers are in the info_teachers df
    invalid_teachers = validate_teachers(dfs, teachers)
    if invalid_teachers != []:
        print(f"Warning: The following teachers appear in constraints but not in info_teachers: {invalid_teachers}")
        return False

    # Check if all appearances of students are in the info_students df
    invalid_students = validate_students(dfs, students)
    if invalid_students != []:
        print(f"Warning: The following students appear in constraints but not in info_students: {invalid_students}")
        return False

    # Check if maximum extra care * number of groups is not less than number of students with extra care
    if n_extra_care > variables.max_extra_care * variables.n_groups:
        print(f"Error: The maximum number of extra care students per group is {variables.max_extra_care}, "
              f"but there are {n_extra_care} students with extra care. "
              f"You need to increase the maximum number of extra care students per group or increase the number of groups.")
        return False

    # Check student preferences
    if not validate_student_preference(dfs, variables, students):
        return False

    # Check constraint consistency
    if not validate_constraints(dfs, variables):
        return False

    return True
