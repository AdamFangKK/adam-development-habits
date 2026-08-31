def evaluate(redacted, owner, access_reviewed, expiry_set):
    return redacted and bool(owner) and access_reviewed and expiry_set
