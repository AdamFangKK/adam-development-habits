def count_paths(rows, columns):
    if rows == 1 or columns == 1:
        return 0
    return count_paths(rows - 1, columns) + count_paths(rows, columns - 1)
