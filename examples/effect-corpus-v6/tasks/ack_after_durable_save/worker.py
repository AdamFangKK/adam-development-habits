class Worker:
    def __init__(self, inbox, store):
        self.inbox = inbox
        self.store = store

    def handle(self, job):
        self.inbox.ack(job["id"])
        self.store.save(job)
        return "saved"
