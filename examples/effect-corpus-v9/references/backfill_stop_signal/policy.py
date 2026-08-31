def evaluate(error_rate, error_limit, lag_seconds, lag_limit):
    return 'stop' if error_rate > error_limit or lag_seconds > lag_limit else 'continue'
