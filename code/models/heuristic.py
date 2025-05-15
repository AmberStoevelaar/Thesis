import os
import csv
from datetime import datetime
import pandas as pd
from help_functions import create_preference_matrix, read_dfs, read_variables

# Helper function to calculate the preference score for a group
def group_preference_score(group, student, preferences):
    return sum(preferences.loc[student, peer] for peer in group)

def greedy_grouping(students, teachers, variables, preferences):
    groups = {teacher: [] for teacher in teachers}

    # Sort students by the number of preferences they have ascending
    students.sort(key=lambda s: preferences.loc[s].sum(), reverse=False)

    # Place each student in the best group
    for student in students:
        best_teacher = None
        best_score = -1

        # Find the best group for student based on preferences
        for teacher in groups:
            group = groups[teacher]
            if len(group) < variables.max_group_size:
                score = group_preference_score(group, student, preferences)
                if score > best_score:
                    best_teacher = teacher
                    best_score = score

        # Assign student to that group
        if best_teacher is not None:
            groups[best_teacher].append(student)

    return groups

def save_results(groups, results_folder, timestamp):
    assignments = [(student, teacher) for teacher, students in groups.items() for student in students]

    df = pd.DataFrame(assignments, columns=['Student', 'Teacher'])
    df = df.sort_values(by='Teacher')

    # Save to CSV
    file_path = os.path.join(results_folder, f"Greedy_{timestamp}.csv")
    df.to_csv(file_path, index=False)

    # Print the resulting groups
    print("Greedy grouping results:")
    print(df)



def run_greedy(school, processed_data_folder):
    data = read_dfs(school, processed_data_folder)
    variables = read_variables(data)

    students = data.info_students['Student'].tolist()
    teachers = data.info_teachers['Teacher'].tolist()

    preference_matrix = create_preference_matrix(data, variables)

    folder ='data/results'
    timestamp = datetime.now().strftime("%d-%m_%H:%M")
    results_folder = os.path.join(folder, school)

    # Run the greedy grouping algorithm
    groups = greedy_grouping(students, teachers, variables, preference_matrix)

    # Save the results
    save_results(groups, results_folder, timestamp)




