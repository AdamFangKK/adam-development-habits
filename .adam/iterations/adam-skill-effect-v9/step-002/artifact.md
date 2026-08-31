# V9 Design Critique 1

The primary endpoint is not sufficiently sensitive to the optimization under test. Commit 97d27dc mainly changes truthful completion states and retention of compound Level 2 decisions under concise output. Hidden code-repair success is valuable but can remain unchanged even if that behavior improves materially. V9 therefore risks a valid but uninformative result.

The next design must add a separate held-out decision scenario cohort with a semantic blind scorer, while preserving the end-to-end repair cohort as the outcome test. The revision must not replace behavioral outcomes with keyword matching or weaken the three-condition isolation and retention rules.
