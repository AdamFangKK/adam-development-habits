from events import version

def decode(event):
    current = version(event)
    if current == 1:
        return {"name": event["name"], "active": bool(event["enabled"])}
    if current == 2:
        return {"name": event["name"], "active": bool(event["active"])}
    raise ValueError("unsupported version")
