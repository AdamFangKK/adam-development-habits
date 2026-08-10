class Inbox:
    def __init__(self):
        self.acknowledged = []

    def ack(self, job_id):
        self.acknowledged.append(job_id)

class Store:
    def __init__(self, fail=False):
        self.fail = fail
        self.saved = []

    def save(self, job):
        if self.fail:
            raise OSError("disk full")
        self.saved.append(job)
