from scipy.stats import truncnorm

def extend_range(min_val, max_val, extend_pct=0.05, lower_bound=0):
    new_min = max(min_val * (1 - extend_pct), lower_bound)
    new_max = max_val * (1 + extend_pct)
    return new_min, new_max

def create_dist(mean, max_val, min_val):
    # Extend the range by 5% on both sides but ensure it does not go below 0
    min_val,  max_val = extend_range(min_val, max_val)

    # Calculate std by dividing the range by 6 (for 99.7% coverage)
    std_dev = abs(max_val - min_val) / 6

    # Truncation limits
    a = (min_val - mean) / std_dev
    b = (max_val - mean) / std_dev

    dist = truncnorm(a, b, loc=mean, scale=std_dev)
    return dist
