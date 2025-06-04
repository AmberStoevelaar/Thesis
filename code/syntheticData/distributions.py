import numpy as np
from scipy.stats import truncnorm
from ranges import compute_summary_stats, get_school_paths
# from code.syntheticData.ranges import compute_summary_stats, get_school_paths

def extend_range(min_val, max_val, extend_pct=0.05, lower_bound=0):
    new_min = max(min_val * (1 - extend_pct), lower_bound)
    new_max = max_val * (1 + extend_pct)
    return new_min, new_max

def create_dist(mean, max_val, min_val, seed):
    # Set seed for reproducibility
    np.random.seed(seed)

    # Calculate std by dividing the range by 6 (for 99.7% coverage)
    std_dev = (max_val - min_val) / 6

    # Truncation limits
    a = (min_val - mean) / std_dev
    b = (max_val - mean) / std_dev

    dist = truncnorm(a, b, loc=mean, scale=std_dev)
    return dist


if __name__ == "__main__":
    folder = 'data/processed_data'
    skip_schools = ["school_1", "school_2", "school_3", "school_4", "school_5", "test_school", ".DS_Store"]
    schools = get_school_paths(folder, skip_schools=skip_schools)
    stats = compute_summary_stats(schools)

    seed = 42
    num_students = 100
    min_gs_dist = create_dist(0.31, 0.49, 0.39, seed=seed)
    sample_value = min_gs_dist.rvs()
    print(sample_value)



