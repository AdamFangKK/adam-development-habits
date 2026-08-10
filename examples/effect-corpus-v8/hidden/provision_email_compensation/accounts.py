class Accounts:
    def __init__(self):
        self.active = set()

    def create(self, user):
        self.active.add(user)

    def deactivate(self, user):
        self.active.discard(user)
