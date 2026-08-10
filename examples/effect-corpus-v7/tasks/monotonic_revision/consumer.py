from store import Store

def consume(store, events):
    for event in events:
        store.apply(event["revision"], event["value"])
    return store.read()
