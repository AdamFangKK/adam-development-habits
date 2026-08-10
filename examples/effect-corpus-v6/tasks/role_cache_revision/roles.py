class RoleStore:
    def __init__(self):
        self.values = {"alice": {"reader"}}
        self.revision = 1

    def roles(self, user):
        return set(self.values.get(user, set()))

    def revoke(self, user, role):
        self.values[user].discard(role)
        self.revision += 1

class Checker:
    def __init__(self, store):
        self.store = store
        self.cache = {}

    def has_role(self, user, role):
        if user not in self.cache:
            self.cache[user] = self.store.roles(user)
        return role in self.cache[user]
