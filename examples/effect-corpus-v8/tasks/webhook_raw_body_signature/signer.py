import hashlib
import hmac

SECRET = b"shared-secret"

def signature(body):
    return hmac.new(SECRET, body.encode("utf-8"), hashlib.sha256).hexdigest()

def valid(body, sent_signature):
    return hmac.compare_digest(signature(body), sent_signature)
