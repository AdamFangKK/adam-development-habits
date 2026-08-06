import importlib.util
import json
import signal
from pathlib import Path


ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("buggy", ROOT / "buggy.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load buggy.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cases = [json.loads(line) for line in (ROOT / "public_cases.json").read_text().splitlines() if line.strip()]


def normalize(value):
    return list(value) if 'longest_common_subsequence' in {"flatten", "kheapsort"} else value


class CallTimeout(Exception):
    pass


def alarm_handler(signum, frame):
    raise CallTimeout("function call exceeded one second")


signal.signal(signal.SIGALRM, alarm_handler)


for input_data, expected in cases:
    signal.setitimer(signal.ITIMER_REAL, 1.0)
    try:
        actual = normalize(getattr(module, 'longest_common_subsequence')(*input_data))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    if actual != expected:
        raise AssertionError(f"input={input_data!r}: expected={expected!r}, actual={actual!r}")

print(f"{len(cases)} public cases passed")
