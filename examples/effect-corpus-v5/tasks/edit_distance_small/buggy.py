def edit_distance(source, target):
    if not source or not target:
        return len(source) or len(target)
    if source[0] == target[0]:
        return 1 + edit_distance(source[1:], target[1:])
    return 1 + min(edit_distance(source, target[1:]), edit_distance(source[1:], target[1:]), edit_distance(source[1:], target))
