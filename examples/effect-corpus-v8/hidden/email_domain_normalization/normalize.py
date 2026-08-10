def canonical_email(email):
    local, domain = email.rsplit("@", 1)
    return local + "@" + domain.lower()
