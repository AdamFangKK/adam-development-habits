def apply_patch(document, patch):
    result = dict(document)
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = value
    return result
