def evaluate(state, recovery_scheduled):
    return state == 'FOUND' or (state == 'UNKNOWN' and recovery_scheduled)
