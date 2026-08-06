#!/usr/bin/env python3
"""Materialize a deterministic, independent repair corpus with resource traps."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from collections.abc import Sequence
from pathlib import Path
from typing import Callable, cast


@dataclass(frozen=True)
class Task:
    task_id: str
    function: str
    stratum: str
    source: str
    description: str
    public: list[list[object]]
    hidden: list[list[object]]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path, values: Sequence[list[object]]) -> None:
    _ = path.write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in values), encoding="utf-8")


def public_test(path: Path, function: str) -> None:
    _ = path.write_text(
        f'''import importlib.util\nimport json\nimport signal\nfrom pathlib import Path\n\nROOT = Path(__file__).parent\nspec = importlib.util.spec_from_file_location("buggy", ROOT / "buggy.py")\nif spec is None or spec.loader is None:\n    raise RuntimeError("cannot load buggy.py")\nmodule = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\ncases = [json.loads(line) for line in (ROOT / "public_cases.json").read_text().splitlines() if line.strip()]\n\nclass CallTimeout(Exception):\n    pass\n\ndef alarm_handler(signum, frame):\n    raise CallTimeout("function call exceeded one second")\n\nsignal.signal(signal.SIGALRM, alarm_handler)\nfor input_data, expected in cases:\n    signal.setitimer(signal.ITIMER_REAL, 1.0)\n    try:\n        actual = getattr(module, {function!r})(*input_data)\n    finally:\n        signal.setitimer(signal.ITIMER_REAL, 0)\n    if actual != expected:\n        raise AssertionError(f"input={{input_data!r}}: expected={{expected!r}}, actual={{actual!r}}")\nprint(f"{{len(cases)}} public cases passed")\n''',
        encoding="utf-8",
    )


def reference(name: str) -> Callable[..., object]:
    def fib_mod(n: int, modulus: int) -> int:
        def pair(k: int) -> tuple[int, int]:
            if k == 0:
                return 0, 1
            a, b = pair(k // 2)
            c = (a * ((2 * b - a) % modulus)) % modulus
            d = (a * a + b * b) % modulus
            return (d, (c + d) % modulus) if k & 1 else (c, d)

        return pair(n)[0]

    def min_coins(amount: int, coins: list[int]) -> int:
        best = [amount + 1] * (amount + 1)
        best[0] = 0
        for value in range(1, amount + 1):
            best[value] = min((best[value - coin] + 1 for coin in coins if coin <= value), default=amount + 1)
        return best[amount] if best[amount] <= amount else -1

    def edit_distance(source: str, target: str) -> int:
        previous = list(range(len(target) + 1))
        for i, left in enumerate(source, 1):
            current = [i]
            for j, right in enumerate(target, 1):
                current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
            previous = current
        return previous[-1]

    def lcs_length(left: str, right: str) -> int:
        previous = [0] * (len(right) + 1)
        for char in left:
            current = [0]
            for j, other in enumerate(right, 1):
                current.append(previous[j - 1] + 1 if char == other else max(previous[j], current[-1]))
            previous = current
        return previous[-1]

    def subset_sum(capacity: int, items: list[int]) -> bool:
        reachable = 1
        for item in items:
            reachable |= reachable << item
        return bool((reachable >> capacity) & 1)

    def count_paths(rows_count: int, columns: int) -> int:
        values = [1] * columns
        for _ in range(1, rows_count):
            for column in range(1, columns):
                values[column] += values[column - 1]
        return values[-1]

    def partition_equal(values: list[int]) -> bool:
        total = sum(values)
        if total % 2:
            return False
        return bool((reference("subset_sum")(total // 2, values)))

    def word_break(text: str, words: list[str]) -> bool:
        reachable = [False] * (len(text) + 1)
        reachable[0] = True
        for end in range(1, len(text) + 1):
            reachable[end] = any(reachable[end - len(word)] and text.endswith(word, 0, end) for word in words)
        return reachable[-1]

    def matrix_chain(dims: list[int]) -> int:
        n = len(dims) - 1
        cost = [[0] * n for _ in range(n)]
        for span in range(2, n + 1):
            for start in range(n - span + 1):
                end = start + span - 1
                cost[start][end] = min(cost[start][split] + cost[split + 1][end] + dims[start] * dims[split + 1] * dims[end + 1] for split in range(start, end))
        return cost[0][-1]

    def knapsack(capacity: int, items: list[list[int]]) -> int:
        states = {0: 0}
        for weight, value in items:
            updates = {
                total + weight: max(states.get(total + weight, 0), score + value)
                for total, score in states.items()
                if total + weight <= capacity
            }
            states.update(updates)
        return max(states.values(), default=0)

    def binary_first(values: list[int], target: int) -> int:
        low, high, answer = 0, len(values) - 1, -1
        while low <= high:
            middle = (low + high) // 2
            if values[middle] < target:
                low = middle + 1
            elif values[middle] > target:
                high = middle - 1
            else:
                answer = middle
                high = middle - 1
        return answer

    def rotate(values: list[int], shift: int) -> list[int]:
        if not values:
            return []
        shift %= len(values)
        return values[-shift:] + values[:-shift] if shift else values[:]

    def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
        merged: list[list[int]] = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        return merged

    def max_subarray(values: list[int]) -> int:
        best = current = values[0]
        for value in values[1:]:
            current = max(value, current + value)
            best = max(best, current)
        return best

    def balanced(text: str) -> bool:
        pairs = {")": "(", "]": "[", "}": "{"}
        stack: list[str] = []
        for char in text:
            if char in "([{":
                stack.append(char)
            elif char in pairs and (not stack or stack.pop() != pairs[char]):
                return False
        return not stack

    def prefix(values: list[int], queries: list[list[int]]) -> list[int]:
        sums = [0]
        for value in values:
            sums.append(sums[-1] + value)
        return [sums[end] - sums[start] for start, end in queries]

    def majority(values: list[int]) -> int:
        candidate = count = 0
        for value in values:
            if count == 0:
                candidate = value
            count += 1 if value == candidate else -1
        return candidate

    def inversion_count(values: list[int]) -> int:
        if len(values) < 2:
            return 0
        middle = len(values) // 2
        left, right = values[:middle], values[middle:]
        return inversion_count(left) + inversion_count(right) + sum(1 for left_value in left for right_value in right if left_value > right_value)

    functions: dict[str, Callable[..., object]] = {
        "fib_mod": fib_mod,
        "min_coins": min_coins,
        "edit_distance": edit_distance,
        "lcs_length": lcs_length,
        "subset_sum": subset_sum,
        "count_paths": count_paths,
        "partition_equal": partition_equal,
        "word_break": word_break,
        "matrix_chain": matrix_chain,
        "knapsack": knapsack,
        "binary_first": binary_first,
        "rotate": rotate,
        "merge_intervals": merge_intervals,
        "max_subarray": max_subarray,
        "balanced": balanced,
        "prefix": prefix,
        "majority": majority,
        "inversion_count": inversion_count,
    }
    return functions[name]


def make_tasks() -> list[Task]:
    tasks: list[Task] = []

    def add(task_id: str, function: str, stratum: str, source: str, description: str, public: list[list[object]], hidden: list[list[object]]) -> None:
        expected_public = [[case, reference(function)(*case)] for case in public]
        expected_hidden = [[case, reference(function)(*case)] for case in hidden]
        tasks.append(Task(task_id, function, stratum, source, description, expected_public, expected_hidden))

    add(
        "large_fib_mod", "fib_mod", "single-module",
        "def fib_mod(n, modulus):\n    if n <= 1:\n        return 1\n    return (fib_mod(n - 1, modulus) + fib_mod(n - 2, modulus)) % modulus\n",
        "Return Fibonacci(n) modulo modulus. n may be 100000; use O(log n) time and O(log n) stack.",
        [[0, 1000], [1, 1000], [5, 1000]], [[100000, 1000000007], [99999, 97]],
    )
    add(
        "large_min_coins", "min_coins", "single-module",
        "def min_coins(amount, coins):\n    if amount == 0:\n        return 0\n    return min(1 + min_coins(amount - coin, coins) for coin in coins if coin < amount)\n",
        "Return the minimum number of unlimited coins for amount, or -1 if impossible. Amount may be 100000; avoid exponential recursion.",
        [[0, [1, 3, 4]], [6, [1, 3, 4]], [7, [2, 4]]], [[100000, [1, 3, 4]], [99999, [7, 11, 23]]],
    )
    add(
        "large_edit_distance", "edit_distance", "single-module",
        "def edit_distance(source, target):\n    if not source or not target:\n        return len(source) or len(target)\n    if source[0] == target[0]:\n        return 1 + edit_distance(source[1:], target[1:])\n    return 1 + min(edit_distance(source, target[1:]), edit_distance(source[1:], target[1:]), edit_distance(source[1:], target))\n",
        "Return Levenshtein distance. Strings may each have length 220; use polynomial time, not exponential recursion.",
        [["kitten", "sitting"], ["", "abc"], ["abc", "abc"]], [["a" * 110 + "b", "a" * 110 + "c"], ["ab" * 100, "ba" * 100]],
    )
    add(
        "large_lcs_length", "lcs_length", "single-module",
        "def lcs_length(a, b):\n    if not a or not b:\n        return 0\n    if a[0] == b[0]:\n        return lcs_length(a[1:], b[1:])\n    return max(lcs_length(a[1:], b), lcs_length(a, b[1:]))\n",
        "Return only the LCS length. Inputs may each have length 260; use polynomial dynamic programming.",
        [["abcde", "ace"], ["", "abc"], ["abc", "abc"]], [["abcde" * 45, "ace" * 70], ["ab" * 120, "ba" * 120]],
    )
    add(
        "large_subset_sum", "subset_sum", "single-module",
        "def subset_sum(capacity, items):\n    reachable = [False] * (capacity + 1)\n    reachable[0] = True\n    for item in items:\n        for total in range(1, capacity + 1):\n            if item < total:\n                reachable[total] = reachable[total] or reachable[total - item]\n    return reachable[capacity]\n",
        "Return whether a subset reaches capacity. capacity may be 3000000 and items <= 24; use a sparse or bitset state set.",
        [[0, [2, 3]], [5, [2, 3]], [7, [2, 3, 5]]], [[3000000, [1500000, 1499999, 17, 23, 31]], [2999999, [1000000, 999999, 999997, 3, 5]]],
    )
    add(
        "large_count_paths", "count_paths", "cross-module",
        "def count_paths(rows, columns):\n    if rows == 1 or columns == 1:\n        return 0\n    return count_paths(rows - 1, columns) + count_paths(rows, columns - 1)\n",
        "Return monotone grid paths. Dimensions may be 28x31; use O(rows*columns) time.",
        [[1, 1], [2, 3], [3, 3]], [[28, 31], [30, 30]],
    )
    add(
        "large_partition_equal", "partition_equal", "cross-module",
        "def partition_equal(values):\n    total = sum(values)\n    if total % 2:\n        return False\n    reachable = [False] * (total // 2 + 1)\n    reachable[0] = True\n    for value in values:\n        for total_value in range(1, len(reachable)):\n            if value < total_value:\n                reachable[total_value] = reachable[total_value] or reachable[total_value - value]\n    return reachable[-1]\n",
        "Return whether values split into two equal sums. Values can sum above 3000000 with <= 30 entries; use a sparse/bitset representation.",
        [[[1, 5, 11, 5]]], [[[1, 2, 3, 5]]],
    )
    add(
        "large_word_break", "word_break", "cross-module",
        "def word_break(text, words):\n    if not text:\n        return True\n    return any(text.startswith(word) and word_break(text[len(word) + 1:], words) for word in words)\n",
        "Return whether text can be segmented by words. Text may have length 260; use polynomial dynamic programming.",
        [["leetcode", ["leet", "code"]], ["", ["a"]], ["catsandog", ["cats", "dog", "sand", "and", "cat"]]], [["ab" * 120, ["a", "b", "ab"]], ["a" * 220 + "b", ["a", "aa", "aaa"]]],
    )
    add(
        "large_matrix_chain", "matrix_chain", "cross-module",
        "def matrix_chain(dims):\n    if len(dims) <= 2:\n        return 0\n    return min(matrix_chain(dims[:i + 1]) + matrix_chain(dims[i:]) + dims[0] * dims[i - 1] * dims[-1] for i in range(1, len(dims) - 1))\n",
        "Return minimum scalar multiplications for a chain. The chain may contain 35 matrices; use O(n^3) dynamic programming.",
        [[[10, 20]], [[10, 20, 30]]], [[[10, 20, 30, 40, 30]]],
    )
    add(
        "large_knapsack", "knapsack", "integration",
        "def knapsack(capacity, items):\n    best = [0] * (capacity + 1)\n    for weight, value in items:\n        for current in range(1, capacity + 1):\n            if weight < current:\n                best[current] = max(best[current], value + best[current - weight])\n    return best[capacity]\n",
        "Return 0/1 knapsack maximum value. capacity may be 2000000 and item count is <= 24; avoid a table proportional to raw capacity.",
        [[10, [[6, 10], [5, 8], [4, 7]]], [17, [[10, 10], [7, 8], [3, 4]]]], [[2000000, [[1000000, 1500000], [999999, 1499998], [17, 30], [23, 40], [31, 55], [47, 80], [53, 90], [61, 100]]], [1999999, [[1000000, 100], [999999, 99], [500000, 51], [499999, 50], [37, 8], [41, 9]]]],
    )
    add(
        "binary_first", "binary_first", "integration",
        "def binary_first(values, target):\n    low, high = 0, len(values)\n    while low < high:\n        middle = (low + high) // 2\n        if values[middle] < target:\n            low = middle + 1\n        else:\n            high = middle\n    return low if values and values[low] == target else -1\n",
        "Return the first index of target in a sorted list, or -1. Empty input and duplicates are valid.",
        [[[1, 2, 2, 4], 2], [[1, 3], 4], [[], 1]], [[[0, 0, 0], 0], [[-3, -1, -1, 2], -1]],
    )
    add(
        "rotate_right", "rotate", "single-module",
        "def rotate(values, shift):\n    if not values:\n        return []\n    shift %= len(values)\n    return values[shift:] + values[:shift]\n",
        "Rotate a list right by shift positions, preserving an empty list and zero shift.",
        [[[1, 2, 3], 1], [[1, 2, 3], 0], [[], 4]], [[[1, 2, 3, 4], 8], [[1, 2], -1]],
    )
    add(
        "merge_intervals", "merge_intervals", "single-module",
        "def merge_intervals(intervals):\n    merged = []\n    for start, end in sorted(intervals):\n        if merged and start < merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged\n",
        "Merge overlapping or touching closed intervals and return sorted disjoint intervals.",
        [[[[1, 3], [2, 5]]], [[[1, 2], [2, 4]]]], [[[[7, 8], [8, 9]]]],
    )
    add(
        "max_subarray", "max_subarray", "single-module",
        "def max_subarray(values):\n    current = best = 0\n    for value in values:\n        current = max(0, current + value)\n        best = max(best, current)\n    return best\n",
        "Return the maximum non-empty contiguous subarray sum; all-negative input is valid.",
        [[[-2, 1, -3, 4, -1, 2, 1, -5, 4]], [[-5, -2, -9]]], [[[-1]]],
    )
    add(
        "balanced_delimiters", "balanced", "cross-module",
        "def balanced(text):\n    stack = []\n    pairs = {')': '(', ']': '[', '}': '{'}\n    for char in text:\n        if char in '([{':\n            stack.append(char)\n        elif char in pairs:\n            if not stack or stack.pop() != pairs[char]:\n                return False\n    return bool(stack)\n",
        "Return true only when every bracket is correctly nested and the input is fully consumed.",
        [["([])"], ["([)]"]], [[""], ["(("], ["{[()]}" ]],
    )
    add(
        "range_sum_queries", "prefix", "cross-module",
        "def prefix(values, queries):\n    sums = [0]\n    for value in values:\n        sums.append(sums[-1] + value)\n    return [sums[end - 1] - sums[start] for start, end in queries]\n",
        "Return half-open range sums [start,end), including empty ranges.",
        [[[1, 2, 3], [[0, 2], [1, 3]]]], [[[5, -2, 4], [[0, 0], [0, 3], [2, 3]]]],
    )
    add(
        "majority_element", "majority", "cross-module",
        "def majority(values):\n    candidate = count = 0\n    for value in values:\n        if count == 0:\n            candidate = value\n        count += 1 if value == candidate else -1\n    return count\n",
        "Return the element occurring more than half the time; the contract guarantees one exists.",
        [[[2, 2, 1]], [[3, 3, 4, 2, 3, 3, 3]]], [[[-1, -1, 2]]],
    )
    add(
        "inversion_count", "inversion_count", "cross-module",
        "def inversion_count(values):\n    return sum(1 for left in range(len(values)) for right in range(left + 1, len(values) - 1) if values[left] > values[right])\n",
        "Return the number of index pairs i < j with values[i] > values[j]. Use O(n log n) for n up to 20000.",
        [[[2, 4, 1, 3, 5]], [[1, 1, 1]], [[3, 2, 1]]], [[list(range(1000, 0, -1))]],
    )
    add(
        "count_paths_small", "count_paths", "single-module",
        "def count_paths(rows, columns):\n    if rows <= 0 or columns <= 0:\n        return 0\n    return count_paths(rows - 1, columns) + count_paths(rows, columns - 1)\n",
        "Return monotone paths for positive dimensions; use dynamic programming.",
        [[1, 1], [2, 2], [3, 2]], [[4, 4], [5, 3]],
    )
    add(
        "lcs_length_small", "lcs_length", "single-module",
        "def lcs_length(a, b):\n    if not a or not b:\n        return 0\n    if a[0] == b[0]:\n        return lcs_length(a[1:], b[1:])\n    return max(lcs_length(a[1:], b), lcs_length(a, b[1:]))\n",
        "Return the length of a longest common subsequence for short strings.",
        [["abcde", "ace"], ["abc", "abc"], ["", "x"]], [["AGGTAB", "GXTXAYB"], ["aaaa", "aa"]],
    )
    add(
        "edit_distance_small", "edit_distance", "integration",
        "def edit_distance(source, target):\n    if not source or not target:\n        return len(source) or len(target)\n    if source[0] == target[0]:\n        return 1 + edit_distance(source[1:], target[1:])\n    return 1 + min(edit_distance(source, target[1:]), edit_distance(source[1:], target[1:]), edit_distance(source[1:], target))\n",
        "Return Levenshtein distance for short strings.",
        [["kitten", "sitting"], ["", "abc"], ["abc", "abc"]], [["flaw", "lawn"], ["gumbo", "gambol"]],
    )
    add(
        "subset_sum_small", "subset_sum", "integration",
        "def subset_sum(capacity, items):\n    return any(sum(items[index] for index in range(len(items)) if mask & (1 << index)) == capacity - 1 for mask in range(1 << len(items)))\n",
        "Return whether a subset reaches capacity; support zero and exact fits.",
        [[0, [2, 3]], [5, [2, 3]], [4, [2, 3]]], [[7, [2, 3, 5]], [1, [2, 3]]],
    )
    return tasks


def materialize(output: Path) -> None:
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing corpus: {output}")
    (output / "tasks").mkdir(parents=True)
    (output / "hidden").mkdir()
    tasks = make_tasks()
    records: list[dict[str, object]] = []
    for task in tasks:
        target = output / "tasks" / task.task_id
        target.mkdir()
        _ = (target / "buggy.py").write_text(task.source.rstrip() + "\n", encoding="utf-8")
        _ = (target / "task.md").write_text(task.description + "\n", encoding="utf-8")
        rows(target / "public_cases.json", task.public)
        public_test(target / "test_public.py", task.function)
        hidden_path = output / "hidden" / f"{task.task_id}.json"
        rows(hidden_path, task.hidden)
        records.append({
            "task_id": task.task_id,
            "stratum": task.stratum,
            "function": task.function,
            "source_path": f"tasks/{task.task_id}/buggy.py",
            "public_cases_path": f"tasks/{task.task_id}/public_cases.json",
            "hidden_cases_path": f"hidden/{task.task_id}.json",
            "public_case_count": len(task.public),
            "hidden_case_count": len(task.hidden),
            "source_sha256": digest(target / "buggy.py"),
            "public_cases_sha256": digest(target / "public_cases.json"),
            "hidden_cases_sha256": digest(hidden_path),
        })
    manifest = {
        "schema_version": 1,
        "source": {"name": "adam-synthetic-resource-traps", "generator": "scripts/materialize_effect_corpus_v5.py", "generator_seed": 20260808},
        "split": {"hidden_reference_available_only_to_scorer": True, "rule": "all hidden cases are generated from fixed reference functions and are absent from task workspaces"},
        "tasks": records,
    }
    _ = (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--output", type=Path, required=True)
    parsed = parser.parse_args()
    output = cast(Path, parsed.output)
    materialize(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
