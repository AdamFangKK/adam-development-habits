def evaluate(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')
