def evaluate(status):
    return status in {408, 429, 500, 502, 503, 504}
