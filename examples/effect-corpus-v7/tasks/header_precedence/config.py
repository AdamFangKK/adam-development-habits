def choose(cli, env, file_value):
    return env or cli or file_value or "production"
