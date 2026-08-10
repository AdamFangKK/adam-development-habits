def receive(event, nonces, handler):
    if nonces.seen(event["nonce"]):
        return "duplicate"
    try:
        handler(event)
    except Exception:
        return "failed"
    nonces.mark(event["nonce"])
    return "ok"
