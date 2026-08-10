def has_scope(token, required):
    return required in token.get("scope", "")
