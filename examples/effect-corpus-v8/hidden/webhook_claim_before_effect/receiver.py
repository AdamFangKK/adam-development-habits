def receive(event, nonces, handler):
    if not nonces.claim(event["nonce"]):
        return "duplicate"
    try:
        handler(event)
    except Exception:
        return "failed"
    return "ok"
