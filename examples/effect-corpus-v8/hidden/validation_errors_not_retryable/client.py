from errors import retryable

def submit(send, payload, attempts=2):
    for _ in range(attempts):
        try:
            return send(payload)
        except Exception as exc:
            if not retryable(exc):
                raise
    return "deferred"
