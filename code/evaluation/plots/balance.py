
def ideal_distribution(total, groups):
    base = total // groups         # 8
    remainder = total % groups     # 2

    # Ideal: fill 'remainder' groups with +1
    ideal_distribution = [base + 1] * remainder + [base] * (groups - remainder)
    return ideal_distribution

def actual_distribution(total, groups):
    actual_distribution = []
    # GET FROM FILES

    return actual_distribution


def normalized_deviation(total, group):
    ideal = ideal_distribution(total, group)
    actual = actual_distribution(total, group)

    # Calculate the normalized deviation
    deviation = sum(abs(a - i) for a, i in zip(actual, ideal))
    normalized_deviation = deviation / total
    return normalized_deviation











if __name__ == "__main__":
    folder = 'final_results'

    





