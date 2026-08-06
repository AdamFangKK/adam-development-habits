def count_paths(rows, columns):
    if rows <= 0 or columns <= 0:
        return 0
    return count_paths(rows - 1, columns) + count_paths(rows, columns - 1)
