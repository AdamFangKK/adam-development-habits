def matrix_chain(dims):
    if len(dims) <= 2:
        return 0
    return min(matrix_chain(dims[:i + 1]) + matrix_chain(dims[i:]) + dims[0] * dims[i - 1] * dims[-1] for i in range(1, len(dims) - 1))
