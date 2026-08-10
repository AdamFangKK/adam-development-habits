class Records:
    def __init__(self):
        self.rows = {"r1": {"tenant": "acme", "value": "old"}}

    def update(self, tenant, record_id, value):
        if record_id not in self.rows:
            raise KeyError(record_id)
        self.rows[record_id]["value"] = value
        return self.rows[record_id]
