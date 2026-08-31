def evaluate(consumers_ready, error_rate, limit):
    return 'contract' if consumers_ready and error_rate <= limit else 'migrate'
