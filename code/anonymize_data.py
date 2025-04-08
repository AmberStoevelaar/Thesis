import pandas as pd
import os
import warnings

warnings.filterwarnings('ignore', category=UserWarning, message='.*Data Validation extension is not supported.*')


def read_data(excel_path):
    # Define sheet names
    sheets = pd.read_excel(excel_path, sheet_name=['Info Docenten', 'Info Leerlingen', 'Groepswensen', 'Eigen Indelingen'], skiprows=1)

    # Read the sheets as dataframes
    info_teachers = sheets['Info Docenten']
    info_students = sheets['Info Leerlingen']
    group_preferences = sheets['Groepswensen']
    current_groups = sheets['Eigen Indelingen']

    # Since group_preferences contains multiple tables, we need to identify the starting and ending rows of each table
    # Find the starting indices for each table (you can adjust this as needed)
    start_table_1 = group_preferences.index[0] + 1
    start_table_2 = group_preferences[group_preferences.iloc[:, 0] == 'Naam Leerling 1'].index[0] + 2
    start_table_3 = group_preferences[group_preferences.iloc[:, 0] == 'Naam Leerling'].index[0] + 2

    # Find the end indices for each table based on the next table's start
    end_table_1 = start_table_2  - 2
    end_table_2 = start_table_3 - 2
    end_table_3 = len(group_preferences) + 1

    # Read each table into a separate dataframe using skiprows and nrows
    group_preferences = pd.read_excel(excel_path, sheet_name='Groepswensen', skiprows=start_table_1, nrows=end_table_1 - start_table_1, header=None)
    constraints_students = pd.read_excel(excel_path, sheet_name='Groepswensen', skiprows=start_table_2, nrows=end_table_2 - start_table_2)
    constraints_teachers = pd.read_excel(excel_path, sheet_name='Groepswensen', skiprows=start_table_3, nrows=end_table_3 - start_table_3)

    # Format the group preferences table
    group_preferences = group_preferences.iloc[1:].reset_index(drop=True).T
    group_preferences.columns = group_preferences.iloc[0]
    group_preferences = group_preferences.drop(0).reset_index(drop=True)
    group_preferences = group_preferences.astype(int)

    return info_teachers, info_students, group_preferences, constraints_students, constraints_teachers, current_groups


def translate_dfs(info_teachers, info_students, group_preferences, constraints_students, constraints_teachers, current_groups):
    # Translate the column names to English
    info_teachers.columns = ['Teacher']
    info_students.columns = ['Student', 'Group', 'Gender', 'Extra Care', 'Extra Care 2', 'Preference 1', 'Preference 2', 'Preference 3', 'Preference 4', 'Preference 5']
    group_preferences.columns = ['Number of Students', 'Number of Groups', 'Minimum Group Size', 'Maximum Number Extra Care 1', 'Maximum Number Extra Care 2']
    constraints_students.columns = ['Student 1', 'Student 2', 'Together']
    constraints_teachers.columns = ['Student', 'Teacher', 'Together']
    current_groups.columns = ['Student', 'Teacher']

    # Translate values in dataframes to English
    info_students['Gender'] = info_students['Gender'].replace({'Jongen': 'Boy', 'Meisje': 'Girl'})
    info_students['Extra Care'] = info_students['Extra Care'].replace({'Ja': 'Yes', 'Nee': 'No'})
    info_students['Extra Care 2'] = info_students['Extra Care 2'].replace({'Ja': 'Yes', 'Nee': 'No'})

    constraints_students['Together'] = constraints_students['Together'].replace({'Ja': 'Yes', 'Nee': 'No'})
    constraints_teachers['Together'] = constraints_teachers['Together'].replace({'Ja': 'Yes', 'Nee': 'No'})

    return info_teachers, info_students, group_preferences, constraints_students, constraints_teachers, current_groups

# Function to replace all occurrences of a string in a DataFrame with the dictionary values
def replace_values(df, column, mapping_dict):
    df[column] = df[column].replace(mapping_dict)
    return df


def anonymize_data(info_teachers, info_students, constraints_students, constraints_teachers, current_groups):
    # Create new Dataframe with student names and assigned id
    studentId = pd.DataFrame()
    teacherId = pd.DataFrame()

    studentId['Student'] = info_students['Student']
    teacherId['Teacher'] = info_teachers['Teacher']

    # Generate a unique ID for each student and teacher
    studentId['ID'] = ['S_' + str(i).zfill(2) for i in range(1, len(studentId) + 1)]
    teacherId['ID'] = ['T_' + str(i).zfill(2) for i in range(1, len(teacherId) + 1)]

    # Create a dictionary to map student and teacher names to IDs
    studentId_dict = dict(zip(studentId['Student'], studentId['ID']))
    teacherId_dict = dict(zip(teacherId['Teacher'], teacherId['ID']))

    # Replace teacher names with IDs in the info_teachers DataFrame
    info_teachers = replace_values(info_teachers, 'Teacher', teacherId_dict)

    # Replace student names with IDs in the info_students DataFrame
    info_students = replace_values(info_students, 'Student', studentId_dict)
    info_students = replace_values(info_students, 'Preference 1', studentId_dict)
    info_students = replace_values(info_students, 'Preference 2', studentId_dict)
    info_students = replace_values(info_students, 'Preference 3', studentId_dict)
    info_students = replace_values(info_students, 'Preference 4', studentId_dict)
    info_students = replace_values(info_students, 'Preference 5', studentId_dict)

    # Replace student names with IDs in the constraints_students DataFrame
    constraints_students = replace_values(constraints_students, 'Student 1', studentId_dict)
    constraints_students = replace_values(constraints_students, 'Student 2', studentId_dict)

    # Replace teacher names with IDs in the constraints_teachers DataFrame
    constraints_teachers = replace_values(constraints_teachers, 'Student', studentId_dict)
    constraints_teachers = replace_values(constraints_teachers, 'Teacher', teacherId_dict)

    # Replace student and teacher names with IDs in the current_groups DataFrame
    current_groups = replace_values(current_groups, 'Student', studentId_dict)
    current_groups = replace_values(current_groups, 'Teacher', teacherId_dict)

    return info_teachers, info_students, constraints_students, constraints_teachers, current_groups, studentId, teacherId


def save_dataframes_to_csv(school, dfs, processed_data_folder, studentId, teacherId):
    # Check if school folder exists
    school_processed_folder = os.path.join(processed_data_folder, school)
    os.makedirs(school_processed_folder, exist_ok=True)

    # Save each dataframe as CSV
    for df_name,df in dfs:
        file_path = os.path.join(school_processed_folder, f'{df_name}.csv')
        df.to_csv(file_path, index=False)

    # Save mapping dictionaries as CSV
    studentId.to_csv(os.path.join(school_processed_folder, 'studentIdMapping.csv'), index=False)
    teacherId.to_csv(os.path.join(school_processed_folder, 'teacherIdMapping.csv'), index=False)



def run_anonymize(school, raw_data_folder, processed_data_folder):
    # Only run anonymization for school if it is not already processed
    school_processed_folder = os.path.join(processed_data_folder, school)
    if not os.path.exists(school_processed_folder):
        os.makedirs(school_processed_folder, exist_ok=True)
    else:
        print("Data for {} already processed.".format(school))
        return

    # Get file path
    school_path = os.path.join(raw_data_folder, school)
    excel_file = [f for f in os.listdir(school_path) if f.endswith('.xlsx')][0]
    excel_path = os.path.join(school_path, excel_file)

    # Read in data
    info_teachers, info_students, group_preferences, constraints_students, constraints_teachers, current_groups = read_data(excel_path)

    # Translate data
    info_teachers, info_students, group_preferences, constraints_students, constraints_teachers, current_groups = translate_dfs(info_teachers, info_students, group_preferences, constraints_students, constraints_teachers, current_groups)

    # Anonymize data
    info_teachers, info_students, constraints_students, constraints_teachers, current_groups, studentId, teacherId = anonymize_data(info_teachers, info_students, constraints_students, constraints_teachers, current_groups)

    # Save the processed data
    dfs = [
        ('info_teachers', info_teachers),
        ('info_students', info_students),
        ('group_preferences', group_preferences),
        ('constraints_students', constraints_students),
        ('constraints_teachers', constraints_teachers),
        ('current_groups', current_groups)
    ]
    save_dataframes_to_csv(school, dfs, processed_data_folder, studentId, teacherId)

    print("Data anonymization for {} completed.".format(school))


# TODO: aanpassen kolommen in vertaling naar goede hoeveelheid/nieuwe namen