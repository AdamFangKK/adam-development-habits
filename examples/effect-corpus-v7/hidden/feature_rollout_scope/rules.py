ENABLED = {("acme", "alice")}

def enabled(tenant, user):
    return (tenant, user) in ENABLED
