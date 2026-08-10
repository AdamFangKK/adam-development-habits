class Clock:
    def __init__(self, values):
        self.values = list(values)

    def now(self):
        return self.values.pop(0)

def run(work, clock, attempts=3, timeout=5):
    for _ in range(attempts):
        deadline = clock.now() + timeout
        try:
            return work()
        except TimeoutError:
            if clock.now() >= deadline:
                return "timed_out"
    return "failed"
