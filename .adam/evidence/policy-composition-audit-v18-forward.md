# Protocol-isolated forward checks

These are two independent fresh-context agent tasks, not a preregistered paired
effect study. Agents received the raw request, raw workspace, current Skill and
relevant normative references only. They were told not to read package tests,
examples, evidence, scoring rubrics, or parent context. Isolation is by protocol
on a shared machine, not an OS sandbox. Parent-side assertions were not supplied
to the agents. Skill wording was subsequently clarified by review; no claim is
made that these runs evaluated a pre-frozen final revision.

## Account normalization

Workspace: `/tmp/adam-forward-JBVNpm`.
Raw request: make CLI and JSON-selected import adapter consistently strip,
casefold and join whitespace with ASCII hyphens; keep existing callable
entrypoints and configured adapter working; standard-library tests only,
workspace edits only, no commit or external services.

Inputs: correct `policy.normalize_key`; duplicate underscore/lower implementation
in `old_policy.py`; CLI and adapter importing old policy; JSON registry selecting
the adapter; current README/docstring saying underscores; historical released
1.0 changelog accurately recording underscores. Supplied tests exercised CLI
and registry entrypoints. Before changes both supplied tests failed.

Agent `forward_v18` reused `policy.normalize_key`, changed the two imports,
replaced the old rule with a direct compatibility re-export, synchronized current
README/docstring, and preserved changelog/registry. Keeping the old callable name
is justified by the raw request to preserve existing callable entrypoints; it
is not evidence that an unconsumed legacy wrapper should always be retained.
Agent added three tests; all five tests passed, including Unicode, whitespace,
empty strings, entrypoint identity and a 100,000-word case.

Parent verification: 9 assertions passed, including 15 additional Unicode and
whitespace outputs, canonical implementation unchanged, supplied tests unchanged,
historical release unchanged, registry unchanged, canonical export identity,
current guidance synchronized, no forced owner/invariant comments, and no
duplicate function in the old module. Output is in the companion forward-checks
artifact. This fixture confirms removal of a duplicate rule, not deletion of all
compatibility names. It provides no production performance claim.

Original input hashes:

| Input | SHA-256 |
| --- | --- |
| request.md | a89624368dd35477c9bedf566a176925050fc94db80a5a7f29cb0d5607b7544e |
| policy.py | b6de3f83f99eedc2d159d488adbefe0306e5b3df7975b38ed3af556068261645 |
| cli.py | d14900422889af420b85f8eaed0e92eee100ea5cff31524d54beeae1ebcd3db1 |
| old_policy.py | eeb68655ba7dfac5995a024b9f61bff550afffdb954cb6be4cd30b911a9a5f84 |
| import_adapter.py | 805fe57567fefbca96197511c7742337e536a718036a071f582c29b0f9910e7d |
| registry.json | b6b5bb7116a8a67d05ff150c30a90b4c0931c8b91dd555d019fb0f574141b551 |
| README.md | 502b8715410f839ead4a78ad80158f156f2bd945936f29939d4e074a59e8e866 |
| CHANGELOG.md | 01f622353f318fc634d7b8ed7631a17070ebb32d20f9e9895717ab1a05b6b0e5 |
| tests/test_accounts.py | 4ffb6c31b66bd2334aeb2fedbb1137176de8ddb43e3fa556513654b9f7eddc47 |

## Read-only tenant price diagnosis

Workspace: `/tmp/adam-diagnosis-ENT6wa`. Raw request: investigate occasional
cross-tenant invoice prices, diagnosis only, read-only local probes, no changes,
commits or network. Raw implementation looked up the catalog by `(tenant, product)`
but indexed a shared cache by `product`. Observations showed 12/12 for north then
south, and 21 for south after restart; catalog values remained 12 and 21.

Agent `diagnosis_forward_v18` reported actual read-only probes: shared north/south
returned [12,12], reversed order [21,21], separate caches [12,21]. Its controlled
in-memory tuple-key intervention passed both orders and alternating requests.
It identified the cache key as the supported local causal owner, rejected wrong
catalog data using observations, and separated local evidence from unknown
deployment/cache-lifecycle/authentication context. It explicitly reported
`Repair status: not applied`; no source repair or production verification claimed.
Its legacy `Causal conclusion: unknown` label refers to unverified repair,
while the diagnosis itself is supported.

Parent verified all three raw files remained byte-identical after the run:
prices.py `9040a18f299475fc27b7052e158f52e3df34407016c52b4a40bdab7401d24a0c`;
observations.txt `6efaf967d8f3ab2ff2ded16a98b2aef9c25dd2d5417071f494df77220700955e`;
request.md `49ddb9cd04f7c4b5dde77aab314c07c4faf1ca727d64f476cdb6b2340364f7ca`.

## Interpretation

Both scenarios showed the intended scoped behavior. They are illustrative,
small, hand-authored cases with no no-Skill control and no blind independent
statistical scorer. They do not establish a success-rate delta, broad transfer,
lower token/latency cost, or an overall model capability increase. Temporary
workspaces are local artifacts and were not added to the Skill distribution.
