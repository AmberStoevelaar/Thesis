import os
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


def ideal_distribution(total, groups):
    base = total // groups
    remainder = total % groups

    ideal_distribution = [base + 1] * remainder + [base] * (groups - remainder)
    return ideal_distribution

def actual_distribution(details):
    actual_distribution = []
    for item in details:
        if item != "total":
            actual_distribution.append(details[item]['count'])

    return actual_distribution

def normalized_deviation(file):
    with open(file) as f:
        data = json.load(f)

    total_deviation = {}
    groups = len(data["group_sizes"])
    for group, categories in data["group_balance"].items():
        for _, details in categories.items():
            total = details["total"]

            ideal = ideal_distribution(total, groups)
            actual = actual_distribution(details)

            # Calculate the normalized deviation
            deviation = sum(abs(a - i) for a, i in zip(actual, ideal))
            normalized_deviation = deviation / total

            if group not in total_deviation:
                total_deviation[group] = 0
            total_deviation[group] = total_deviation[group] + normalized_deviation

    return total_deviation

def total_deviations(folder):
    file_paths = get_file_paths(folder)

    total_deviation = {}
    for file_path in file_paths:
        print(f"filename: {file_path}")
        filename = file_path.split('/')[-1]
        method = filename.split('_')[0]

        deviation = normalized_deviation(file_path)
        if method not in total_deviation:
            total_deviation[method] = {i: [] for i in deviation}

        for attr, value in deviation.items():
            if attr not in total_deviation[method]:
                total_deviation[method][attr] = []
            total_deviation[method][attr].append(value)

    return total_deviation

def plot(folder):
    total_deviation = total_deviations(folder)
    methods = list(total_deviation.keys())
    attributes = sorted({attr for d in total_deviation.values() for attr in d})

    avg_data = {attr: [np.mean(total_deviation[method].get(attr, [0])) for method in methods] for attr in attributes}
    std_data = {attr: [np.std(total_deviation[method].get(attr, [0])) for method in methods] for attr in attributes}

    x = np.arange(len(methods))
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, attr in enumerate(attributes):
        offsets = x + (i - len(attributes)/2) * width + width/2
        ax.bar(offsets, avg_data[attr], width, yerr=std_data[attr], label=attr, capsize=5)

    ax.set_xlabel('Method')
    ax.set_ylabel('Average Normalized Deviation')
    ax.set_title('Attribute Deviation per Method')
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.legend(title="Attribute")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the plot
    plt.savefig(os.path.join("plots", "balance.png"), dpi=300)

    plt.show()



if __name__ == "__main__":
    folder = 'final_results'
    os.makedirs(os.path.join(folder, 'plots'), exist_ok=True)

    school = "Vorige"
    filename = "CP_23-05_12:15.json"

    file_path = os.path.join(folder, school, 'evals', filename)
    plot(folder)





