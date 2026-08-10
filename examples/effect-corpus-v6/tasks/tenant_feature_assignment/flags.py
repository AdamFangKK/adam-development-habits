def targeting_key(tenant, user):
    return user

def enabled(tenant, user):
    return targeting_key(tenant, user)
