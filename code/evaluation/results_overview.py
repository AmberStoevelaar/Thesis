

def show_counts(merged):
    # Count the number of students in each group
    group_counts = merged['Assigned Group'].value_counts().sort_index()

    # Count gender in each Assigned_Group
    gender_counts = merged.groupby("Assigned Group")["Gender"].value_counts().unstack().fillna(0)

    # Count Group (4/5) in each Assigned_Group
    grade_counts = merged.groupby("Assigned Group")["Grade"].value_counts().unstack().fillna(0)

    # Count extra care students
    extra_care_counts = merged.groupby("Assigned Group")["Extra Care"].value_counts().unstack().fillna(0)

    # Print the results
    print("Number of students in each group:")
    print(group_counts)

    print("Gender count per assigned group:")
    print(gender_counts)

    print("\Grade count per assigned group:")
    print(grade_counts)

    print("Extra care count per assigned group:")
    print(extra_care_counts)

