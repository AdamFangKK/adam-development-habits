def inversion_count(values):
    return sum(1 for left in range(len(values)) for right in range(left + 1, len(values) - 1) if values[left] > values[right])
