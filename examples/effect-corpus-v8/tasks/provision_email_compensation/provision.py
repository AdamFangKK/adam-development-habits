def provision(user, accounts, billing, mailer):
    accounts.create(user)
    billing.charge(user)
    try:
        mailer(user)
    except Exception:
        return "failed"
    return "active"
