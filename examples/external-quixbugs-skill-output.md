Evidence ledger:

- Change level: Level 1, Causal Lite
- Canonical owner: `python_programs/shortest_paths.py`
- Changed file: `python_programs/shortest_paths.py`
- Observed symptom: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q python_testcases/test_shortest_paths.py` failed `3` tests; reachable non-source nodes stayed `inf`.
- Primary hypothesis: Bellman-Ford relaxation was writing updated distances into `weight_by_edge[(u, v)]` instead of `weight_by_node[v]`.
- Alternative hypothesis: distance initialization omitted required reachable nodes.
- Discriminating check: `{('A', 'B'): 1, ('B', 'C'): 2}` returned `{'B': inf, 'C': inf, 'A': 0}` and mutated edge `('B', 'C')` to `inf`, showing the relaxation target was wrong.
- Invariant: relaxation must update destination-node distances monotonically and must not mutate the input edge-weight mapping.
- Repair: changed relaxation assignment from `weight_by_edge[u, v] = ...` to `weight_by_node[v] = ...`.
- Verification: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q python_testcases/test_shortest_paths.py` -> `3 passed in 0.01s`
- Sanity check after repair: same two-edge graph returned `{'B': 1, 'C': 3, 'A': 0}` and preserved `{('A', 'B'): 1, ('B', 'C'): 2}`.
- Causal conclusion classification: root-cause fix.
