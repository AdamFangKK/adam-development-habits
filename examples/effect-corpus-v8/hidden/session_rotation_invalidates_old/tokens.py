class Tokens:
    def __init__(self):
        self.current = {}
        self.valid = set()

    def issue(self, user, token):
        previous = self.current.get(user)
        if previous is not None:
            self.valid.discard(previous)
        self.current[user] = token
        self.valid.add(token)

    def verify(self, user, token):
        return self.current.get(user) == token and token in self.valid
