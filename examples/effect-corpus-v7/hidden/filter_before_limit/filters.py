def matches(row, status):
    return status is None or row["status"] == status
