# Secure Code Paths

Use this reference only when the Secure Code Path Gate applies. Treat all data that crosses a trust boundary as untrusted until the responsible server-side boundary has validated it and enforced policy. A check at one layer does not make another sink safe.

Record the relevant path as `source -> validation/normalization -> authorization or policy -> sink`. Keep only the categories touched by the change; this is a focused code review, not a repository-wide security audit.

## Injection and Output Contexts

- **Database or query construction:** Bind values through the repository's parameterized query or ORM API. Do not concatenate, interpolate, or hand-escape data into a query. Keep query structure controlled by code, and constrain dynamic identifiers or sort fields with a fixed allowlist.
- **Process execution:** Prefer a direct library API. When a process is necessary, pass an argument vector without a shell, keep executable and subcommand selection in trusted code, and allowlist any caller-selected option. Bound input, timeout, output, and working directory.
- **HTML, templates, headers, redirects, and logs:** Encode for the exact output context through the framework's escaping mechanism. Treat raw HTML, template fragments, response headers, and redirect targets as privileged data paths; use an allowlist or a reviewed sanitizer designed for that context. Never rely on a generic string replacement to make every context safe.

## Authorization and Resource Ownership

- Authenticate and authorize at the server-side operation boundary, including background jobs and internal endpoints. A UI condition, route name, or caller-provided role does not establish permission.
- Resolve the requested resource through the authenticated tenant or owner scope before read, update, delete, download, or privileged action. Keep identifiers opaque where the contract permits, but never treat opacity as authorization.
- Make policy decisions in a canonical owner and return a stable denied outcome without exposing sensitive existence, credential, or internal-policy details.

## Files, URLs, Parsing, and Resource Abuse

- **Files and uploads:** Use generated server-side names, an allowlisted content policy, size and count limits, and a canonicalized path constrained to an intended root. Re-check the resolved target before sensitive file operations and avoid following attacker-controlled archive paths or links outside that root.
- **Outbound URL fetches:** Parse before use; allow only required schemes, hosts, ports, and destinations. Reject loopback, link-local, private, or otherwise disallowed address ranges according to the deployment policy, re-check redirects, and use timeout, body-size, and redirect limits.
- **Parsing and deserialization:** Prefer schema-bound, data-only formats and parsers with explicit size/depth limits. Do not deserialize untrusted data into executable objects, invoke dynamic type loading, or enable external entity/resource resolution unless the use case is explicitly bounded and independently reviewed.
- **Caller-controlled resource use:** Set payload, pagination, recursion, concurrency, queue, query, and time limits before work begins. Test the failure or cancellation path as well as the ordinary response.

## Secrets and Cryptography

- Do not put credentials, tokens, keys, raw payloads, or personal data in source, logs, traces, test fixtures, reports, or error messages. Reuse the repository's secret/configuration boundary and redact before recording diagnostics.
- Use established platform cryptography and key-management APIs; do not invent algorithms, protocols, key derivation, or random-token construction. Confirm key scope, rotation or expiry, and failure behavior when a change handles secrets.

## Security Finding Verification

For a code review or scanner alert, do not report a vulnerability solely because a pattern matches. Establish the affected source, sink, path reachability, trust boundary, existing control, and realistic impact. Classify each finding as one of:

- `confirmed`: the path reaches a sensitive sink without a sufficient control; include a focused remediation and a regression test.
- `excluded`: the path is unreachable or a verified control is sufficient; record the evidence, responsible owner, and expiry or review condition for any suppression.
- `unknown`: the available code, configuration, or runtime evidence cannot establish reachability or the control's behavior; do not suppress the alert or claim the path is safe.

Use repository-native SAST, dependency, and secret scans when available. Do not add a security dependency, alter scanner severity, or create a broad ignore rule merely to satisfy this reference. Treat a missing scanner as a verification gap and report it plainly.

## Verification

For each triggered category, add the narrowest meaningful tests to the repository's existing suite:

1. A valid request or input completes through the intended authorized path.
2. The relevant malformed, unauthorized, disallowed, or oversized input is rejected or contained before the sensitive sink.
3. Minimal synthetic malicious inputs are permitted in local tests and fixtures when needed to prove the control. Keep real secrets, personal data, and production payloads out of every test. Do not echo test inputs into logs, reports, snapshots, or externally shared artifacts.

For Level 2 changes, have the independent review explicitly trace the data flow and verify that framework defaults actually apply in the changed configuration. A passing unit test does not prove a control covers a different route, worker, tenant, output context, or redirect path.
