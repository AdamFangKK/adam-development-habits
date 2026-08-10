def enabled(values):
    value = values.get("enabled")
    return True if value is None else bool(value)
