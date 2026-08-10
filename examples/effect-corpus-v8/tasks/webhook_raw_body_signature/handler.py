import json
from signer import valid

def accept(raw_body, sent_signature):
    normalized = json.dumps(json.loads(raw_body), sort_keys=True, separators=(",", ":"))
    return valid(normalized, sent_signature)
