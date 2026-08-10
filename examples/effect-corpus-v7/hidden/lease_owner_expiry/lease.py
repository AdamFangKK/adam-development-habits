class Lease:
    def __init__(self):
        self.owner = None
        self.expires = 0

    def acquire(self, owner, now, ttl):
        if self.owner is not None and now < self.expires:
            return False
        self.owner = owner
        self.expires = now + ttl
        return True

    def renew(self, owner, now, ttl):
        if self.owner != owner or now >= self.expires:
            raise PermissionError("lease not owned")
        self.expires = now + ttl
        return True
