def handle(event, provider, store):
    try:
        provider.send(event)
    except TimeoutError:
        return "pending"
    store.append(event)
    return "ack"
