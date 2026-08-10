from filters import matches

def query(rows, status=None, limit=10):
    return [row for row in rows[:limit] if matches(row, status)]
