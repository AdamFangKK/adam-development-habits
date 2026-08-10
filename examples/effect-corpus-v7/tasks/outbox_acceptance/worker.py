def handle(event, provider, store):
    provider.send(event)
    return "ack"
