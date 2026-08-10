def deliver(ledger, event, send):
    prior = ledger.find(event)
    if prior is not None:
        return prior
    result = send(event)
    ledger.save(event, result)
    return result
