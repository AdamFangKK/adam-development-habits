from lease import Lease

def heartbeat(lease, owner, now, ttl):
    return lease.renew(owner, now, ttl)
