import os
from collections import defaultdict
import json
import numpy as np
import matplotlib.pyplot as plt

def get_file_paths(folder):
    all_files = []
    for school in os.listdir(folder):
        school_path = os.path.join(folder, school)
        if os.path.isdir(school_path):
            for fname in os.listdir(school_path):
                if fname.endswith(".json"):
                    all_files.append(os.path.join(school_path, fname))

    return all_files

def satisfaction_rates(folder):
    file_paths = get_file_paths(folder)
    method_satisfaction = defaultdict(list)

    for file_path in file_paths:
        filename = file_path.split('/')[-1]
        method = filename.split('_')[0]

        with open(file_path, 'r') as f:
            data = json.load(f)
            satisfaction_rate = data.get("satisfaction_rate")
            if satisfaction_rate is not None:
                method_satisfaction[method].append(satisfaction_rate)

    return method_satisfaction

def average_satisfaction(folder):
    method_satisfaction = satisfaction_rates(folder)
    stats = {}

    for method, rates in method_satisfaction.items():
        mean = np.mean(rates)
        std = np.std(rates)
        stats[method] = (mean, std)

    print("Average Satisfaction Rates with Standard Deviations:")
    for method, (mean, std) in stats.items():
        print(f"{method}: mean = {mean:.3f}, std = {std:.3f}")

    return stats

def plot(stats):
    methods = list(stats.keys())
    means = [stats[m][0] for m in methods]
    stds = [stats[m][1] for m in methods]

    _, ax = plt.subplots(figsize=(3.5, 2.5))
    x = np.arange(len(methods))
    bar_width = 0.6

    ax.bar(x, means, yerr=stds, width=bar_width, capsize=3,
           color='skyblue', edgecolor='black', error_kw=dict(elinewidth=1))

    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=45, ha='right')
    ax.set_xlabel('Method')
    ax.set_ylabel('Average\nSatisfaction Rate', labelpad=4)
    ax.set_ylim(0, 1)
    ax.tick_params(axis='y', pad=2)
    ax.set_title('AverageSatisfaction Rate by Method', fontsize=10)
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.show()






if __name__ == "__main__":
    # school = sys.argv[1]
    # folder = os.path.join("final_results", school)
    folder = 'final_results'

    stats = average_satisfaction(folder)
    plot(stats)




