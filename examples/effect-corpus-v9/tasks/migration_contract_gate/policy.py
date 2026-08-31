def evaluate(consumers_ready, error_rate, limit):
    return 'contract' if error_rate <= limit else 'migrate'
