import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

def get_file_paths(folder):
    all_files = []
    for school in os.listdir(folder):
        if school == 'plots':
            continue
        school_path = os.path.join(folder, school, 'logs')
        if os.path.isdir(school_path):
            for fname in os.listdir(school_path):
                if fname.endswith(".csv"):
                    all_files.append((school, os.path.join(school_path, fname)))
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
    sns.set(style='whitegrid')
    fig, ax = plt.subplots(figsize=(12, 6))
    palette = sns.color_palette('muted', n_colors=len(data))

    for i, (times, values, label) in enumerate(data):
        if label in ["ILPSOFT", "CPSOFT"]:
            continue
        ax.step(times, values, where='post', label=label, color=palette[i])

    ax.set_xlabel("Elapsed Time (s)", fontsize=16)
    ax.set_ylabel("Objective Value", fontsize=16)
    ax.set_title(f"Objective Value over Time for Task {school}", fontsize=18)

    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

    ax.legend(loc='lower right', fontsize=14, frameon=False, title='')

    ax.tick_params(axis='both', which='major', labelsize=14)
    fig.tight_layout()

    output_path = os.path.join("final_results", "plots", f"{school}_progress.png")
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    folder = 'final_results'
    os.makedirs(os.path.join(folder, 'plots'), exist_ok=True)

    files = get_file_paths(folder)

    # Group files by school to plot once per school
    from collections import defaultdict
    school_files = defaultdict(list)
    for school, fpath in files:
        school_files[school].append(fpath)

    for school, fpaths in school_files.items():
        data = [parse_result_file(f) for f in fpaths if parse_result_file(f) is not None]
        data = sorted(data, key=lambda x: 0 if x[2].upper() == "CP" else 1)
        plot_results(data, school)
