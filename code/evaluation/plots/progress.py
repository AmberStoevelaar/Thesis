import os
import sys
import matplotlib.pyplot as plt
import pandas as pd

def get_file_paths(folder, school):
    all_files = []
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


def parse_result_file(path):
    with open(path, 'r') as f:
        lines = f.readlines()
    data_start = header_row(lines)

    optimal_found = any("OPTIMAL" in line for line in lines)
    df = pd.read_csv(path, skiprows=data_start)

    times = []
    values = []
    last_time = 0
    last_obj = None

    for _, row in df.iterrows():
        t = row["Elapsed Time (s)"]
        obj = row["Objective Value"]

        if last_obj is not None:
            times.extend([last_time, t])
            values.extend([last_obj, last_obj])

        last_time = t
        last_obj = obj

    if last_obj is not None:
        times.append(last_time)
        values.append(last_obj)
        if not optimal_found:
            times.append(last_time + 50)
            values.append(last_obj)

    filename = os.path.basename(path)
    method = filename.split('_')[0]
    label = method
    return times, values, label

def plot_results(data, school):
    plt.figure(figsize=(3.5, 2.5))  # ACM double-column width

    for times, values, label in data:
        if label in ["ILPSOFT", "CPSOFT"]:
            continue
        plt.step(times, values, where='post', label=label)

    plt.xlabel("Elapsed Time (s)", labelpad=4)
    plt.ylabel("Objective Value", labelpad=4)
    plt.title("Objective vs Time", fontsize=10)

    plt.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    # Compact legend
    plt.legend(loc='upper right', fontsize=7, frameon=False, handlelength=2)

    output_path = os.path.join("final_results/plots", f"{school}_progress.png")
    plt.savefig(output_path, bbox_inches='tight')

    plt.show()



if __name__ == "__main__":
    school = sys.argv[1]
    folder = 'final_results'
    os.makedirs(os.path.join(folder, 'plots'), exist_ok=True)

    files = get_file_paths(folder, school)
    data = [parse_result_file(f) for f in files if parse_result_file(f) is not None]
    plot_results(data, school)







