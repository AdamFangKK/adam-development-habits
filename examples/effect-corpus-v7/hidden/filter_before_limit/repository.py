from filters import matches

def query(rows, status=None, limit=10):
    filtered = [row for row in rows if matches(row, status)]
    return filtered[:limit]
