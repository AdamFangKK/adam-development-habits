class Tokens:
    def __init__(self):
        self.current = {}
        self.valid = set()

    def issue(self, user, token):
        self.current[user] = token
        self.valid.add(token)

    def verify(self, user, token):
        return token in self.valid
