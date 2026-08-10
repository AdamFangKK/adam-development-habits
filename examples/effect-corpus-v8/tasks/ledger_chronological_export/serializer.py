def serialize(entries):
    return sorted(entries, key=lambda entry: entry["account"])
