def evaluate(accepted, rejection, idempotent):
    return (not accepted) and rejection == 'retryable_preacceptance' and idempotent
