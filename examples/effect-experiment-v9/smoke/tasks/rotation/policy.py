def evaluate(values, distance):
    return tuple(values[distance:] + values[:distance])
