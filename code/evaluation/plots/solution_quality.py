import os
from collections import defaultdict
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

def plot_satisfaction_rate(stats):
    methods = list(stats.keys())
    means = [stats[m][0] for m in methods]
    stds = [stats[m][1] for m in methods]

    _, ax = plt.subplots(figsize=(3.5, 2.5))
    x = np.arange(len(methods))
    bar_width = 0.6

    ax.bar(x, means, yerr=stds, width=bar_width, capsize=3,
           color='skyblue', edgecolor='black', error_kw=dict(elinewidth=1))

    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.set_xlabel('Method')
    ax.set_ylabel('Average\nSatisfaction Rate', labelpad=4)
    ax.set_ylim(0, 1)
    ax.tick_params(axis='y', pad=2)
    ax.set_title('Average Satisfaction Rate by Method', fontsize=10)
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    output_path = os.path.join("final_results/plots", "satisfaction_rate.png")
    plt.savefig(output_path, bbox_inches='tight')

    plt.show()

def minimum_preferences(folder):
    file_paths = get_file_paths(folder)
    method_minprefs = defaultdict(list)

    for file_path in file_paths:
        filename = os.path.basename(file_path)
        method = filename.split('_')[0]

        with open(file_path, 'r') as f:
            data = json.load(f)
            min_pref = data.get("minimum_preferences")
            if min_pref is not None:
                method_minprefs[method].append(min_pref)

    return method_minprefs

def average_minimum_preferences(folder):
    method_minprefs = minimum_preferences(folder)
    stats = {}

    for method, prefs in method_minprefs.items():
        mean = np.mean(prefs)
        std = np.std(prefs)
        stats[method] = (mean, std)

    print("Average Minimum Preferences with Std Dev:")
    for method, (mean, std) in stats.items():
        print(f"{method}: mean = {mean:.3f}, std = {std:.3f}")

    return stats

def plot_minimum_preferences(stats):
    methods = list(stats.keys())
    means = [stats[m][0] for m in methods]
    stds = [stats[m][1] for m in methods]

    _, ax = plt.subplots(figsize=(3.5, 2.5))
    x = np.arange(len(methods))
    bar_width = 0.6

    ax.bar(x, means, yerr=stds, width=bar_width, capsize=3,
           color='skyblue', edgecolor='black', error_kw=dict(elinewidth=1))

    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.set_xlabel('Method')
    ax.set_ylabel('Average\nMinimum Preferences', labelpad=4)
    ax.set_ylim(0, 5)
    ax.tick_params(axis='y', pad=2)
    ax.set_title('Average Minimum Preferences by Method', fontsize=10)
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    output_path = os.path.join("final_results/plots", "minimum_preferences.png")
    plt.savefig(output_path, bbox_inches='tight')

    plt.show()


if __name__ == "__main__":
    folder = 'final_results'
    os.makedirs(os.path.join(folder, 'plots'), exist_ok=True)

    satisfaction_rate_stats = average_satisfaction(folder)
    plot_satisfaction_rate(satisfaction_rate_stats)

    min_prefs_stats = average_minimum_preferences(folder)
    plot_minimum_preferences(min_prefs_stats)
