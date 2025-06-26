import os
import json
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

def parse_normalized_above_min(folder):
    file_paths = get_file_paths(folder)
    records = []

    for path in file_paths:
        parts = path.split(os.sep)
        task_id = parts[-3]
        filename = os.path.basename(path)
        method = filename.split('_')[0].lower()

        with open(path, 'r') as f:
            data = json.load(f)
            above_min = data.get('more_than_minimum_percentage')
            satisfaction_rate = data.get('satisfaction_rate')

            if above_min is not None and satisfaction_rate and satisfaction_rate > 0:
                normalized_value = above_min / satisfaction_rate
                records.append({
                    'Task': task_id,
                    'Method': method.upper(),
                    'Normalized Above Min': normalized_value
                })

    return pd.DataFrame(records)

def plot_normalized_above_min(df, output_path):
    # Sort tasks on number of students
    custom_task_order = ['1', '4', '2', '5', '6', '7', '8', '3', '9', '10', '11', '12']
    df['Task'] = pd.Categorical(df['Task'], categories=custom_task_order, ordered=True)
    df = df.sort_values('Task')

    hue_order = ['CP', 'ILP']
    df['Method'] = pd.Categorical(df['Method'], categories=hue_order, ordered=True)

    sns.set(style='whitegrid')
    fig, ax = plt.subplots(figsize=(12, 6))

    barplot = sns.barplot(
        data=df,
        x='Task', y='Normalized Above Min', hue='Method',
        hue_order=hue_order,
        ax=ax
    )

    # Calculate averages for each method
    avg_cp = df[df['Method'] == 'CP']['Normalized Above Min'].mean()
    avg_ilp = df[df['Method'] == 'ILP']['Normalized Above Min'].mean()
    print("AVG CP: ", avg_cp)
    print("AVG ILP: ", avg_ilp)

    # Plot dashed average lines with same colors as bars
    ax.axhline(avg_cp, color='tab:blue', linestyle='--', linewidth=1.5, label='CP Avg')
    ax.axhline(avg_ilp, color='tab:orange', linestyle='--', linewidth=1.5, label='ILP Avg')

    ax.set_ylabel('Normalized Proportion of Students Exceeding Minimum', fontsize=16)
    ax.set_xlabel('Task', fontsize=16)
    ax.set_title('Normalized Proportion of Students Exceeding Minimum Preferences per Task', fontsize=18)
    ax.tick_params(axis='x', rotation=0)
    ax.legend(title='', fontsize=14, loc='upper right')
    ax.tick_params(axis='both', which='major', labelsize=14)
    fig.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    input_folder = "final_results"
    output_file = os.path.join(input_folder, "plots", "normalized_above_minimum.png")

    df = parse_normalized_above_min(input_folder)
    plot_normalized_above_min(df, output_file)

