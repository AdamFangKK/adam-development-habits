from normalize import canonical_email

def account_key(email):
    return canonical_email(email)
