import os

def inside(base, candidate):
    base = os.path.abspath(os.path.normpath(base))
    candidate = os.path.abspath(os.path.normpath(candidate))
    try:
        return os.path.commonpath([base, candidate]) == base
    except ValueError:
        return False
