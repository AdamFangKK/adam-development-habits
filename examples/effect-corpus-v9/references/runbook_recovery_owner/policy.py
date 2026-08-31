def evaluate(diagnosis, recovery, rollback, owner):
    return diagnosis and recovery and rollback and bool(owner)
