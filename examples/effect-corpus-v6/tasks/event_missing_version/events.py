def parse(event):
    version = event.get("version", 2)
    if version == 1:
        return {"name": event["name"]}
    return {"name": event["payload"]["name"]}
