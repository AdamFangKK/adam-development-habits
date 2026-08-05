Changed `python_programs/shortest_paths.py`.

Causal reasoning: the Bellman-Ford relaxation loop was computing candidate distances correctly, but storing them into `weight_by_edge[(u, v)]` instead of `weight_by_node[v]`, so returned node distances never improved. I also initialized distances for every node appearing in any edge.

Verification: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q python_testcases/test_shortest_paths.py` -> `3 passed in 0.01s`.
