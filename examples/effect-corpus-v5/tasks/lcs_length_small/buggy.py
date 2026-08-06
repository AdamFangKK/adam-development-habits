def lcs_length(a, b):
    if not a or not b:
        return 0
    if a[0] == b[0]:
        return lcs_length(a[1:], b[1:])
    return max(lcs_length(a[1:], b), lcs_length(a, b[1:]))
