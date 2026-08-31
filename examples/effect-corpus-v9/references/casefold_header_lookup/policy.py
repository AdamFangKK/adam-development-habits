def evaluate(headers, name):
    return next((value for key, value in headers.items() if key.lower() == name.lower()), None)
