import os
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def parse_balance_deviation(folder):
    records = []
    for task in os.listdir(folder):
        eval_path = os.path.join(folder, task, 'evals')
        if not os.path.isdir(eval_path):
            continue
        for fname in os.listdir(eval_path):
            if not fname.endswith('.json'):
                continue
            method = fname.split('_')[0].upper()
            path = os.path.join(eval_path, fname)
            with open(path, 'r') as f:
                data = json.load(f)
                deviations = data.get('balance_deviation', {})
                for attr, value in deviations.items():
                    records.append({
                        'Task': task,
                        'Method': method,
                        'Attribute': attr,
                        'Deviation': value
                    })
    return pd.DataFrame(records)

def plot_balance_deviation_with_error_bars(df, output_path):
    sns.set(style='whitegrid')
    fig, ax = plt.subplots(figsize=(12, 6))

    # Capitalize and filter attributes
    df['Attribute'] = df['Attribute'].str.capitalize()
    df = df[~df['Attribute'].isin(['Behavior', 'Balance', 'Total'])]

    hue_order = ['CP', 'ILP']

    sns.barplot(
        data=df,
        x='Attribute',
        y='Deviation',
        hue='Method',
        order=['Gender', 'Grade', 'Extra care'],
        hue_order=hue_order,
        ci='sd',
        capsize=0.1,
        palette='muted',
        errwidth=1,
        ax=ax
    )

    ax.set_xlabel('Attribute', fontsize=16)
    ax.set_ylabel('Mean Balance Deviation', fontsize=16)
    ax.set_title('Average Balance Deviation per Attribute and Method', fontsize=18)
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.legend(title='', loc='upper right', fontsize=14)
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == '__main__':
    input_folder = 'final_results'
    output_file = os.path.join(input_folder, 'plots', 'balance_deviation.png')

    df = parse_balance_deviation(input_folder)
    plot_balance_deviation_with_error_bars(df, output_file)
