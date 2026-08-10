def run(dependencies, clock, budget):
    deadline = clock.now() + budget
    for dependency in dependencies:
        if clock.now() >= deadline:
            raise TimeoutError("budget exhausted")
        dependency(clock, deadline)
    return "ok"
