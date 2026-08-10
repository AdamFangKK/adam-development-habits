def login(tokens, user, token):
    tokens.issue(user, token)
    return token

def authorized(tokens, user, token):
    return tokens.verify(user, token)
