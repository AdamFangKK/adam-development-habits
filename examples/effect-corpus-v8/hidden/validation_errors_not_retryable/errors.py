def retryable(exc):
    return isinstance(exc, TimeoutError)
