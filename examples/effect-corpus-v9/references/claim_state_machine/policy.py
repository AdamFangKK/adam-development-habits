def evaluate(command_ran, acceptance_met):
    return 'planned' if not command_ran else ('verified' if acceptance_met else 'executed')
