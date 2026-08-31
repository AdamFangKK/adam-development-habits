def evaluate(default, file_value, env_value):
    return env_value if env_value is not None else (file_value if file_value is not None else default)
