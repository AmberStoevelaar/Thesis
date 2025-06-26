import os
import json
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def get_file_paths(folder):
    all_files = []
    for task in os.listdir(folder):
        eval_path = os.path.join(folder, task, 'evals')
        if os.path.isdir(eval_path):
            for fname in os.listdir(eval_path):
                if fname.endswith(".json"):
                    all_files.append(os.path.join(eval_path, fname))
    return all_files

def parse_time_results(folder):
    file_paths = get_file_paths(folder)
    records = []

    for path in file_paths:
        parts = path.split(os.sep)
        task_id = parts[-3]
        filename = os.path.basename(path)
        method = filename.split('_')[0].lower()

        with open(path, 'r') as f:
            data = json.load(f)
            feasible_time = data.get("time_to_first_feasible", np.nan)
            opt_time = data.get("time_to_optimal_or_timeout", np.nan)

            # If not optimal, set optimal_time to NaN to avoid plotting it
            if data.get("final_status", "").lower() != "optimal":
                opt_time = np.nan

            records.append({
                "Task": task_id,
                "Method": method.upper(),
                "Feasible Time": feasible_time,
                "Optimal Time": opt_time
            })

    return pd.DataFrame(records)

def plot_time_metric(df, metric_col, output_path, title):
    # Sort tasks on number of students
    custom_task_order = ['1', '4', '2', '5', '6', '7', '8', '3', '9', '10', '11', '12']
    df['Task'] = pd.Categorical(df['Task'], categories=custom_task_order, ordered=True)
    df = df.sort_values('Task')

    # Order methods so CP is always left of ILP
    hue_order = ['CP', 'ILP']

    sns.set(style='whitegrid')
    fig, ax = plt.subplots(figsize=(12, 6))

    sns.barplot(
        data=df,
        x='Task', y=metric_col, hue='Method',
        hue_order=hue_order,
        ax=ax
    )

    # Compute averages per method
    avg_cp = df[df['Method'] == 'CP'][metric_col].mean()
    avg_ilp = df[df['Method'] == 'ILP'][metric_col].mean()
    print("AVG CP: ", avg_cp)
    print("AVG ILP: ", avg_ilp)

    # filter df for tasks where both found optimal
    shared_opt = df_times.dropna().groupby('Task').filter(lambda g: len(g) == 2)
    avg_cp_shared = shared_opt[shared_opt["Method"] == "CP"]["Optimal Time"].mean()
    avg_ilp_shared = shared_opt[shared_opt["Method"] == "ILP"]["Optimal Time"].mean()

    print("AVG SHARED CP: ", avg_cp_shared)
    print("AVG SHARED ILPP: ", avg_ilp_shared)


    # Plot dashed horizontal average lines
    ax.axhline(avg_cp, color='tab:blue', linestyle='--', linewidth=1.5, label='CP Avg')
    ax.axhline(avg_ilp, color='tab:orange', linestyle='--', linewidth=1.5, label='ILP Avg')

    ax.set_ylabel('Runtime (seconds)', fontsize=16)
    ax.set_xlabel('Task', fontsize=16)
    ax.set_title(title, fontsize=18)
    ax.set_yscale('log')
    ax.tick_params(axis='x', rotation=0)
    ax.grid(axis='y', alpha=0.7)

    # Combine legend entries
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), title='Method', fontsize=14)

    ax.yaxis.set_major_formatter(plt.ScalarFormatter())
    ax.yaxis.get_major_formatter().set_scientific(False)

    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    input_folder = "final_results"
    plot_folder = os.path.join(input_folder, "plots")
    os.makedirs(plot_folder, exist_ok=True)

    df_times = parse_time_results(input_folder)

    plot_time_metric(
        df_times,
        "Feasible Time",
        os.path.join(plot_folder, "feasible_times_per_task.png"),
        "Time to Feasible Solution per Task"
    )

    plot_time_metric(
        df_times,
        "Optimal Time",
        os.path.join(plot_folder, "optimal_times_per_task.png"),
        "Time to Optimal Solution per Task"
    )
