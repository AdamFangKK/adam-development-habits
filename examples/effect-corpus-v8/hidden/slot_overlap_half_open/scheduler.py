from policy import overlaps

def can_add(existing, candidate):
    return all(not overlaps(slot, candidate) for slot in existing)
