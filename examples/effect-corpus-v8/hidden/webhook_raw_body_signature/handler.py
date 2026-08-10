from signer import valid

def accept(raw_body, sent_signature):
    return valid(raw_body, sent_signature)
