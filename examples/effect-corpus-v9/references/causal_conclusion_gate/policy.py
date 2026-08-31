def evaluate(intervention_executed, reproduction_removed):
    return 'root-cause fix' if intervention_executed and reproduction_removed else 'unknown'
