import os
import pandas as pd

def get_file_paths(folder):
    all_files = []
    for school in os.listdir(folder):
        if school == 'plots':
            continue
        school_path = os.path.join(folder, school, 'logs')
        if os.path.isdir(school_path):
            for fname in os.listdir(school_path):
                if fname.endswith(".csv"):
                    all_files.append(os.path.join(school_path, fname))
    return all_files

def header_row(lines):
    for i, line in enumerate(lines):
        if line.startswith("Timestamp"):
            return i
    return None

def get_objectives(path):
    with open(path, 'r') as f:
        lines = f.readlines()
    data_start = header_row(lines)
    if data_start is None:
        return None, None

    df = pd.read_csv(path, skiprows=data_start)
    if df.empty or len(df) < 2:
        return None, None

    initial_obj = df.iloc[0]["Objective Value"]
    final_obj = df.iloc[-2]["Objective Value"]  # Second-to-last row

    return initial_obj, final_obj

def main():
    folder = 'final_results'
    files = get_file_paths(folder)

    cp_initial_values = []
    cp_final_values = []
    ilp_initial_values = []
    ilp_final_values = []

    for fpath in files:
        filename = os.path.basename(fpath)
        method = filename.split('_')[0].upper()
        initial_obj, final_obj = get_objectives(fpath)

        if initial_obj is None or final_obj is None:
            continue

        if method == "CP":
            print("Initial Objective Value for CP:", initial_obj, fpath)
            cp_initial_values.append(initial_obj)
            cp_final_values.append(final_obj)
        elif method == "ILP":
            print("Initial Objective Value for ILP:", initial_obj, fpath)
            ilp_initial_values.append(initial_obj)
            ilp_final_values.append(final_obj)

    def avg(values):
        return sum(values) / len(values) if values else None

    print(f"Average initial objective value for CP: {avg(cp_initial_values)}")
    print(f"Average final objective value for CP: {avg(cp_final_values)}")
    print(f"Average initial objective value for ILP: {avg(ilp_initial_values)}")
    print(f"Average final objective value for ILP: {avg(ilp_final_values)}")

if __name__ == "__main__":
    main()



