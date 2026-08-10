def provision(user, accounts, billing, mailer):
    accounts.create(user)
    charged = False
    try:
        billing.charge(user)
        charged = True
        mailer(user)
    except Exception:
        if charged:
            billing.refund(user)
        accounts.deactivate(user)
        return "failed"
    return "active"
