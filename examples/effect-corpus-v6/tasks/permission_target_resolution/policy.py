ACL = {"public": {"alice"}, "secret": {"admin"}}

def allowed(user, resource):
    return user in ACL.get(resource, set())
