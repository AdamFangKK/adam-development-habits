def evaluate(environment, authorized):
    return environment != 'production' or authorized
