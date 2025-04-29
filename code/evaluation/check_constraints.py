import math

def violates_min_group_size(group, df, min_group_size):
    # Check if the group size is less than the minimum group size
    count = df[df["Assigned Group"] == group].shape[0]
    if count < min_group_size:
        return True
    return False

def violates_max_group_size(group, df, max_group_size):
    count = df[df["Assigned Group"] == group].shape[0]
    if count > max_group_size:
        return True
    return False

def violates_max_extra_care(group, df, max_extra_care_1):
    # Check if the group size is greater than the maximum extra care size
    count = df[(df["Assigned Group"] == group) & (df["Extra Care"] == "Yes")].shape[0]
    if count > max_extra_care_1:
        return True
    return False

def violates_student_pair(group, df, constraints_students):
    students = df[df['Assigned Group'] == group]['Student'].tolist()
    violations = []

    for _, row in constraints_students.iterrows():
        s1, s2, together = row['Student 1'], row['Student 2'], row['Together']

        s1_in_group = s1 in students
        s2_in_group = s2 in students
        # print(f"Checking constraint for students {s1} and {s2}: {together} in group {group}")
        # print(f"Student {s1} in group: {s1_in_group}, Student {s2} in group: {s2_in_group}")

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
        # teacher_in_group = teacher in df[df['Assigned Group'] == group]['Teacher'].tolist()
        # Check if teacher is the group
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

def violates_ratio(group, df, attribute, deviation, variables):
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




def run_check_constraints(groups, merged, data, variables):
    for group in groups:
        # Check if the group size is less than the minimum group size
        if violates_min_group_size(group, merged, variables.min_group_size):
            print(f"Group {group} violates minimum group size with size {len(merged[merged['Assigned Group'] == group])}.")
            return False

        # Check if the group size is greater than the maximum group size
        if violates_max_group_size(group, merged, variables.max_group_size):
            print(f"Group {group} violates maximum group size with size {len(merged[merged['Assigned Group'] == group])}.")
            return False

        # Check if there are invalid students paired in group
        student_pair_violations = violates_student_pair(group, merged, data.constraints_students)
        if student_pair_violations:
            for s1, s2, reason in student_pair_violations:
                print(f"Student {s1} and {s2} violate the constraint: {reason}.")
            return False

        # Check if there are invalid students paired with teacher in group
        teacher_pair_violations = violates_teacher_pair(group, merged, data.constraints_teachers)
        if teacher_pair_violations:
            for s, t, reason in teacher_pair_violations:
                print(f"Student {s} and teacher {t} violate the constraint: {reason}.")
            return False

        # Check if gender ratio is violated
        if violates_ratio(group, merged, "Gender", 0.1, variables):
            print(f"Group {group} violates Gender ratio.")
            return False

        # Check if grade ratio is violated
        if violates_ratio(group, merged, "Group", 0.1, variables):
            print(f"Group {group} violates Grade ratio.")
            return False


    return True
