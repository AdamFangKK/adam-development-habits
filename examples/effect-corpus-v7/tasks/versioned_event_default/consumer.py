from events import version

def decode(event):
    current = version(event)
    if current == 1:
        return {"name": event["name"], "active": bool(event["enabled"])}
    return {"name": event["name"], "active": event["active"]}
