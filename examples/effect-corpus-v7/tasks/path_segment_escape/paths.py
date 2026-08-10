import os

def inside(base, candidate):
    base = os.path.normpath(base)
    candidate = os.path.normpath(candidate)
    return candidate.startswith(base)
