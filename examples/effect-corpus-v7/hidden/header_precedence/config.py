def choose(cli, env, file_value):
    if cli is not None:
        return cli
    if env is not None:
        return env
    return file_value if file_value is not None else "production"
