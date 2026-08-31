def evaluate(changed_paths, task_paths):
    return tuple(path for path in changed_paths if path in set(task_paths))
