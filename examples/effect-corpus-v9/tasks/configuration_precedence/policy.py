def evaluate(default, file_value, env_value):
    return env_value or file_value or default
