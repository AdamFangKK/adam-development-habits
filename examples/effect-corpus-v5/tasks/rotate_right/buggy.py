def rotate(values, shift):
    if not values:
        return []
    shift %= len(values)
    return values[shift:] + values[:shift]
