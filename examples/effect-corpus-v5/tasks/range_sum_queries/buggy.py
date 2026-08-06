def prefix(values, queries):
    sums = [0]
    for value in values:
        sums.append(sums[-1] + value)
    return [sums[end - 1] - sums[start] for start, end in queries]
