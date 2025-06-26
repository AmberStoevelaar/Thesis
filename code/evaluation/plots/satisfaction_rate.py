import os
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

def get_file_paths(folder):
    all_files = []
    for task in os.listdir(folder):
        eval_path = os.path.join(folder, task, 'evals')
        if os.path.isdir(eval_path):
            for fname in os.listdir(eval_path):
                if fname.endswith(".json"):
                    all_files.append(os.path.join(eval_path, fname))
    return all_files

def parse_results(folder):
    file_paths = get_file_paths(folder)
    records = []

    for path in file_paths:
        parts = path.split(os.sep)
        task_id = parts[-3]
        filename = os.path.basename(path)
        method = filename.split('_')[0].lower()

        with open(path, 'r') as f:
            data = json.load(f)
            rate = data.get('satisfaction_rate')
            if rate is not None:
                records.append({
                    'Task': task_id,
                    'Method': method.upper(),
                    'Satisfaction Rate': rate * 100
                })
    return pd.DataFrame(records)

def plot_satisfaction(df, output_path):
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
        x='Task', y='Satisfaction Rate', hue='Method',
        hue_order=hue_order,
        ax=ax
    )

    # Compute averages per method
    avg_cp = df[df['Method'] == 'CP']['Satisfaction Rate'].mean()
    avg_ilp = df[df['Method'] == 'ILP']['Satisfaction Rate'].mean()
    print(f"Average satisfaction rate for CP: {avg_cp:.2f}%")
    print(f"Average satisfaction rate for ILP: {avg_ilp:.2f}%")

    # Plot dashed average lines with same colors as bars, add to legend
    ax.axhline(avg_cp, color='tab:blue', linestyle='--', linewidth=1.5, label='CP Avg')
    ax.axhline(avg_ilp, color='tab:orange', linestyle='--', linewidth=1.5, label='ILP Avg')

    ax.set_ylabel('Satisfaction Rate (%)', fontsize=16)
    ax.set_xlabel('Task', fontsize=16)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title('Satisfaction Rate per Task', fontsize=18)
    ax.tick_params(axis='x', rotation=0)

    # Combine legend entries
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), title='', fontsize=14, loc='upper right')

    ax.tick_params(axis='both', which='major', labelsize=14)
    fig.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    input_folder = "final_results"
    output_file = os.path.join(input_folder, "plots", "satisfaction_rate.png")
    df = parse_results(input_folder)

    # Compute and print average satisfaction rates
    avg_rates = df.groupby("Method")["Satisfaction Rate"].mean()
    for method, avg in avg_rates.items():
        print(f"Average satisfaction rate for {method}: {avg:.2f}%")

    plot_satisfaction(df, output_file)
