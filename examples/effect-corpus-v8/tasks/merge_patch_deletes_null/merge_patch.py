def apply_patch(document, patch):
    result = dict(document)
    for key, value in patch.items():
        if value is not None:
            result[key] = value
    return result
