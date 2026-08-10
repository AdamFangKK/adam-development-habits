from policy import allowed

TARGETS = {"alias": "secret"}
DATA = {"public": "hello", "secret": "classified"}

def resolve(path):
    return TARGETS.get(path, path)

def read(user, path):
    target = resolve(path)
    if not allowed(user, path):
        raise PermissionError("forbidden")
    return DATA[target]
