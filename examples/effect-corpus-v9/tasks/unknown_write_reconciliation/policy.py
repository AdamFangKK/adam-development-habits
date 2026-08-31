def evaluate(state):
    return 'finalize' if state == 'FOUND' else 'resend'
