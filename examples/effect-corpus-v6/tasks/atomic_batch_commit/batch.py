class Store:
    def __init__(self, fail_at=None):
        self.rows = []
        self.fail_at = fail_at

    def commit(self, rows):
        for index, row in enumerate(rows):
            if self.fail_at == index:
                raise OSError("transient write")
            self.rows.append(row)

class Batch:
    def __init__(self, store):
        self.store = store

    def process(self, rows):
        try:
            self.store.commit(rows)
            return "ok"
        except OSError:
            return "retry"
