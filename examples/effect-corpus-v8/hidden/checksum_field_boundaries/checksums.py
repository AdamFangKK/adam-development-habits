import hashlib

def digest(fields):
    payload = "".join(f"{len(field)}:{field}" for field in fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
