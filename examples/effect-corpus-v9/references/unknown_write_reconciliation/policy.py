def evaluate(state):
    return {'FOUND': 'finalize', 'ABSENT': 'resend', 'UNKNOWN': 'preserve_pending'}[state]
