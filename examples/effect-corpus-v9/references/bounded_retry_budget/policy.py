def evaluate(attempt, max_attempts, transient, idempotent):
    return transient and idempotent and attempt < max_attempts
