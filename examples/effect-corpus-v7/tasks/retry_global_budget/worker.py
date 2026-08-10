def run(dependencies, clock, budget):
    for dependency in dependencies:
        deadline = clock.now() + budget
        dependency(clock, deadline)
    return "ok"
