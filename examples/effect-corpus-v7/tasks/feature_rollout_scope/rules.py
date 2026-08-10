ENABLED = {("acme", "alice")}

def enabled(tenant, user):
    return user == "alice"
