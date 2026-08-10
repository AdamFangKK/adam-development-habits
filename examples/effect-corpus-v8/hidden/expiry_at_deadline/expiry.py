def expired(now, issued_at, ttl):
    return now >= issued_at + ttl
