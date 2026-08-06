def majority(values):
    candidate = count = 0
    for value in values:
        if count == 0:
            candidate = value
        count += 1 if value == candidate else -1
    return count
