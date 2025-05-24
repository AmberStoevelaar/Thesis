import os
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt

def get_file_paths(folder):
    all_files = []
    for school in os.listdir(folder):
        school_path = os.path.join(folder, school, 'evals')
        if os.path.isdir(school_path):
            for fname in os.listdir(school_path):
                if fname.endswith(".json"):
                    all_files.append(os.path.join(school_path, fname))

    return all_files

def load_results(folder):
    file_paths = get_file_paths(folder)
    records = []

    for file_path in file_paths:
        filename = os.path.basename(file_path)
        method = filename.split('_')[0]

        with open(file_path, 'r') as f:
            data = json.load(f)

        group_sizes = data.get("group_sizes", {})
        total_students = sum(group_sizes.values()) if group_sizes else 1

        feasible_time = data["time_to_first_feasible"] / total_students
        opt_time = data["time_to_optimal_or_timeout"]

        # Handle optimal: only count it if declared and within time limit
        if (data["final_status"]).lower() == "optimal":
            optimal_time = opt_time / total_students
        else:
            optimal_time = np.nan  # will skip in mean

        records.append({
            "method": method,
            "feasible_time": feasible_time,
            "optimal_time": optimal_time
        })
    return pd.DataFrame(records)

def summarize_by_method(folder):
    df = load_results(folder)
    summary = df.groupby("method").agg(
        avg_feasible_time=("feasible_time", "mean"),
        std_feasible_time=("feasible_time", "std"),
        avg_optimal_time=("optimal_time", "mean"),
        std_optimal_time=("optimal_time", "std"),
        count_optimal=("optimal_time", "count"),
    ).reset_index()

    summary["std_feasible_time"] = summary["std_feasible_time"].fillna(0)
    summary["std_optimal_time"] = summary["std_optimal_time"].fillna(0)
    return summary

def plot(summary):
    methods = summary['method']
    x = np.arange(len(methods))  # the label locations

    width = 0.35  # width of the bars

    fig, ax = plt.subplots(figsize=(8,5))

    # Bars for feasible time
    rects1 = ax.bar(x - width/2, summary['avg_feasible_time'], width,
                    yerr=summary['std_feasible_time'], label='Avg Feasible Time', capsize=5)

    # Bars for optimal time
    rects2 = ax.bar(x + width/2, summary['avg_optimal_time'], width,
                    yerr=summary['std_optimal_time'], label='Avg Optimal Time', capsize=5)

    ax.set_ylabel('Time per student (seconds)')
    ax.set_title('Solver Times per Method')
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Optional: add numbers on top of bars
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            if not np.isnan(height):
                ax.annotate(f'{height:.2f}',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # offset label a bit above bar
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=8)

    autolabel(rects1)
    autolabel(rects2)

    plt.tight_layout()
    plt.savefig('plots/time_per_method.png', dpi=300)
    plt.show()







if __name__ == "__main__":
    folder = 'final_results'
    os.makedirs("plots", exist_ok=True)

    summary = summarize_by_method(folder)
    print(summary)
    plot(summary)








