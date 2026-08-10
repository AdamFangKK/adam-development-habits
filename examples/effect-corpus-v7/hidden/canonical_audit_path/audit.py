from resolver import resolve

def record(user, path):
    return {"user": user, "resource": path}

def read_and_record(user, path):
    resolved = resolve(path)
    return resolved, record(user, resolved)
