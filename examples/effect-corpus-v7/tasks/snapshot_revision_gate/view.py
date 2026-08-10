from state import Store

def refresh(store, revision, value):
    store.publish(revision, value)
    return store.read()
