import math

try:
    from .helpers import get_minimum_preferences_satisfied
except ImportError:
    from helpers import get_minimum_preferences_satisfied

# 1. Each student should be assigned to exactly one group.
def violates_unique_teacher_assignment(df):
    return df['Student'].duplicated().any()

# 2. Each group should have between min_group_size and max_group_size students.
def violates_max_group_size(group, groups, max_group_size):
    return len(groups[group]) >= max_group_size

def violates_min_group_size(group, groups, min_group_size):
    return len(groups[group]) < min_group_size

# 3. Pairing constraints for students and teacher
def violates_student_pair(group, df, constraints_students):
    students = df[df['Assigned Group'] == group]['Student'].tolist()
    violations = []

    for _, row in constraints_students.iterrows():
        s1, s2, together = row['Student 1'], row['Student 2'], row['Together']

        s1_in_group = s1 in students
        s2_in_group = s2 in students

        if together == 'Yes':
            # Inclusion constraint: both should be in the same group
            if s1_in_group != s2_in_group:  # one is in the group, the other is not
                violations.append((s1, s2, 'Should be together'))
        else:
            # Exclusion constraint: both should not be in the same group
            if s1_in_group and s2_in_group:
                violations.append((s1, s2, 'Should not be together'))

    return violations

def violates_teacher_pair(group, df, constraints_teachers):
    students =  df[df['Assigned Group'] == group]['Student'].tolist()
    violations = []

    for _, row in constraints_teachers.iterrows():
        student, teacher, together = row['Student'], row['Teacher'], row['Together']

        student_in_group = student in students
        teacher_in_group = group == teacher

        if together == 'Yes':
            # Inclusion constraint: both should be in the same group
            if student_in_group != teacher_in_group:  # one is in the group, the other is not
                violations.append((student, teacher, 'Should be together'))
        else:
            # Exclusion constraint: both should not be in the same group
            if student_in_group and teacher_in_group:
                violations.append((student, teacher, 'Should not be together'))

    return violations

# 4. Each group should have a maximum number of students with extra care or any other binary attribute.
def violates_max_extra_care(group, df, max_extra_care):
    return df[(df["Assigned Group"] == group) & (df["Extra Care"] == "Yes")].shape[0] > max_extra_care

# 5. Each group should have a balanced ratio of students based on certain attributes.
def violates_ratio(group, df, attribute, variables, deviation=0.1):
    categories = df[attribute].unique()
    category_counts = df[attribute].value_counts().to_dict()
    target_per_group = {cat: category_counts[cat] / variables.n_groups for cat in categories}

    students = df[df['Assigned Group'] == group]

    # Check if each category falls within the deviation range
    for cat in categories:
        actual = students[students[attribute] == cat].shape[0]
        target = target_per_group[cat]
        lower_bound = math.floor((1 - deviation) * target)
        upper_bound = math.ceil((1 + deviation) * target)

        if not (lower_bound <= actual <= upper_bound):
            return True

    return False

# 6. Check if all students have at least min_preferences satisfied if they provided as much.
def violates_min_prefs(df, min_prefs):
    min_satisfied = get_minimum_preferences_satisfied(df)
    return min_satisfied < min_prefs



# Returns True if the constraints are satisfied, False otherwise
def run_check_constraints(groups, merged, data, variables, min_prefs=1, deviation=0.1):
    # 1. Check if all students are assigned to exactly one group
    if violates_unique_teacher_assignment(merged):
        print("Some students are assigned to multiple groups.")
        return False

    # 6. Check if all students have at least min_preferences satisfied
    if violates_min_prefs(merged, min_prefs):
        print(f"Some students have less than {min_prefs} preferences satisfied.")
        return False

    for group in groups:
        # 2. Check if group size is within the allowed range
        if violates_min_group_size(group, merged, variables.min_group_size):
            print(f"Group {group} violates minimum group size with size {len(merged[merged['Assigned Group'] == group])}.")
            return False

        if violates_max_group_size(group, merged, variables.max_group_size):
            print(f"Group {group} violates maximum group size with size {len(merged[merged['Assigned Group'] == group])}.")
            return False

        # 3. Check if there are invalid pairings of students and teachers
        student_pair_violations = violates_student_pair(group, merged, data.constraints_students)
        if student_pair_violations:
            for s1, s2, reason in student_pair_violations:
                print(f"Student {s1} and {s2} violate the constraint: {reason}.")
            return False

        teacher_pair_violations = violates_teacher_pair(group, merged, data.constraints_teachers)
        if teacher_pair_violations:
            for s, t, reason in teacher_pair_violations:
                print(f"Student {s} and teacher {t} violate the constraint: {reason}.")
            return False

        # 4. Check if group has too many students with extra care
        if violates_max_extra_care(group, merged, variables.max_extra_care):
            print(f"Group {group} violates maximum extra care constraint.")
            return False

        # 5. Check if groups are balanced within a certain ratio
        if violates_ratio(group, merged, "Gender", variables, deviation):
            print(f"Group {group} violates Gender ratio.")
            return False

        if violates_ratio(group, merged, "Grade", variables, deviation):
            print(f"Group {group} violates Grade ratio.")
            return False

        if violates_ratio(group, merged, "Extra Care", variables, deviation):
            print(f"Group {group} violates Extra Care ratio.")
            return False

        # Optionally check behavior if attribute is present
        if "Behavior" in merged.columns:
            if violates_ratio(group, merged, "Behavior", 0.1, variables):
                print(f"Group {group} violates Behavior ratio.")
                return False

    return True
