def evaluate(state, recovery_scheduled):
    return state == 'FOUND' or recovery_scheduled
