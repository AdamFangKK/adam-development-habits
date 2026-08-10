from rules import enabled

def visible(tenant, user):
    return enabled(tenant, user)
