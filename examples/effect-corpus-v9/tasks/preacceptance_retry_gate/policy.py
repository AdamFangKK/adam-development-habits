def evaluate(accepted, rejection, idempotent):
    return rejection in {'transient', 'retryable_preacceptance'}
