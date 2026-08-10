TARGETS = {"/shortcut": "/documents/secret"}

def resolve(path):
    return TARGETS.get(path, path)
