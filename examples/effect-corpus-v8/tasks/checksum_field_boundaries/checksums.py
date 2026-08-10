import hashlib

def digest(fields):
    payload = "".join(fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
