#!/usr/bin/env python3
"""Materialize a fresh v7 multi-file causal-repair corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import cast


PUBLIC_COMMAND = ["python3", "-m", "unittest", "discover", "-s", "tests"]


def code(value: str) -> str:
    return textwrap.dedent(value).lstrip()


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    stratum: str
    description: str
    source: dict[str, str]
    fixed: dict[str, str]
    public_test: str
    hidden_test: str


def spec(task_id: str, stratum: str, description: str, source: dict[str, str], fixed: dict[str, str], public_test: str, hidden_test: str) -> TaskSpec:
    return TaskSpec(task_id, stratum, description, source, fixed, code(public_test), code(hidden_test))


def make_tasks() -> list[TaskSpec]:
    return [
        spec("cursor_exclusivity", "single-module", "A page endpoint treats its end cursor as inclusive and returns one extra item.",
            {"pager.py": code('''
                def page(items, start, end):
                    if start < 0 or end < start:
                        raise ValueError("invalid range")
                    return items[start:end + 1]
            ''')},
            {"pager.py": code('''
                def page(items, start, end):
                    if start < 0 or end < start:
                        raise ValueError("invalid range")
                    return items[start:end]
            ''')},
            '''
                import unittest
                from pager import page

                class Public(unittest.TestCase):
                    def test_end_cursor_is_exclusive(self):
                        self.assertEqual(page(["a", "b", "c"], 0, 2), ["a", "b"])
            ''',
            '''
                import unittest
                from pager import page

                class Hidden(unittest.TestCase):
                    def test_middle_empty_and_invalid_ranges(self):
                        self.assertEqual(page(["a", "b", "c", "d"], 1, 3), ["b", "c"])
                        self.assertEqual(page(["a"], 1, 1), [])
                        with self.assertRaises(ValueError):
                            page(["a"], 2, 1)
            '''),
        spec("config_false_default", "single-module", "A configuration reader replaces an explicit false value with the default.",
            {"settings.py": code('''
                def enabled(values):
                    return values.get("enabled") or True
            ''')},
            {"settings.py": code('''
                def enabled(values):
                    value = values.get("enabled")
                    return True if value is None else bool(value)
            ''')},
            '''
                import unittest
                from settings import enabled

                class Public(unittest.TestCase):
                    def test_explicit_false_is_preserved(self):
                        self.assertFalse(enabled({"enabled": False}))
            ''',
            '''
                import unittest
                from settings import enabled

                class Hidden(unittest.TestCase):
                    def test_missing_and_false_are_distinct(self):
                        self.assertTrue(enabled({}))
                        self.assertFalse(enabled({"enabled": 0}))
                        self.assertTrue(enabled({"enabled": "yes"}))
            '''),
        spec("casefold_identity", "single-module", "A case-insensitive identity check misses Unicode case folding equivalence.",
            {"identity.py": code('''
                def same(left, right):
                    return left.lower() == right.lower()
            ''')},
            {"identity.py": code('''
                def same(left, right):
                    return left.casefold() == right.casefold()
            ''')},
            '''
                import unittest
                from identity import same

                class Public(unittest.TestCase):
                    def test_unicode_casefolding(self):
                        self.assertTrue(same("Straße", "STRASSE"))
            ''',
            '''
                import unittest
                from identity import same

                class Hidden(unittest.TestCase):
                    def test_casefolding_and_non_match(self):
                        self.assertTrue(same("WEIß", "weiss"))
                        self.assertFalse(same("alpha", "alphabet"))
            '''),
        spec("path_segment_escape", "single-module", "A path containment check accepts a sibling directory with the same prefix.",
            {"paths.py": code('''
                import os

                def inside(base, candidate):
                    base = os.path.normpath(base)
                    candidate = os.path.normpath(candidate)
                    return candidate.startswith(base)
            ''')},
            {"paths.py": code('''
                import os

                def inside(base, candidate):
                    base = os.path.abspath(os.path.normpath(base))
                    candidate = os.path.abspath(os.path.normpath(candidate))
                    try:
                        return os.path.commonpath([base, candidate]) == base
                    except ValueError:
                        return False
            ''')},
            '''
                import unittest
                from paths import inside

                class Public(unittest.TestCase):
                    def test_sibling_prefix_is_outside(self):
                        self.assertFalse(inside("/srv/app", "/srv/app2/data"))
            ''',
            '''
                import unittest
                from paths import inside

                class Hidden(unittest.TestCase):
                    def test_boundaries_and_normalization(self):
                        self.assertTrue(inside("/srv/app", "/srv/app/data/../logs"))
                        self.assertFalse(inside("/srv/app", "/srv/application"))
            '''),
        spec("round_half_even", "single-module", "A monetary formatter rounds decimal text with half-up arithmetic instead of the declared half-even rule.",
            {"rounding.py": code('''
                def cents(value):
                    return int(float(value) * 100 + 0.5) / 100
            ''')},
            {"rounding.py": code('''
                from decimal import Decimal, ROUND_HALF_EVEN

                def cents(value):
                    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
            ''')},
            '''
                import unittest
                from rounding import cents

                class Public(unittest.TestCase):
                    def test_tie_rounds_to_even(self):
                        self.assertEqual(cents("2.345"), 2.34)
            ''',
            '''
                import unittest
                from rounding import cents

                class Hidden(unittest.TestCase):
                    def test_both_even_and_odd_ties(self):
                        self.assertEqual(cents("2.345"), 2.34)
                        self.assertEqual(cents("2.355"), 2.36)
                        self.assertEqual(cents("2.346"), 2.35)
            '''),
        spec("stable_dedup_order", "single-module", "A deduplication helper loses the source order required by the API.",
            {"dedup.py": code('''
                def unique(items):
                    return sorted(set(items))
            ''')},
            {"dedup.py": code('''
                def unique(items):
                    seen = set()
                    result = []
                    for item in items:
                        if item not in seen:
                            seen.add(item)
                            result.append(item)
                    return result
            ''')},
            '''
                import unittest
                from dedup import unique

                class Public(unittest.TestCase):
                    def test_first_occurrence_order(self):
                        self.assertEqual(unique(["b", "a", "b", "c"]), ["b", "a", "c"])
            ''',
            '''
                import unittest
                from dedup import unique

                class Hidden(unittest.TestCase):
                    def test_order_and_unhashable_rejection_are_stable(self):
                        self.assertEqual(unique([3, 1, 3, 2, 1]), [3, 1, 2])
                        with self.assertRaises(TypeError):
                            unique([[1], [1]])
            ''') ,
        spec("locale_cache_namespace", "cross-module", "A localized catalog cache omits locale from its key and leaks one locale into another.",
            {"policy.py": code('''
                def key(locale, product):
                    return "product:" + product
            '''), "catalog.py": code('''
                from policy import key

                class Catalog:
                    def __init__(self, values):
                        self.values = values
                        self.cache = {}

                    def label(self, locale, product):
                        cache_key = key(locale, product)
                        if cache_key not in self.cache:
                            self.cache[cache_key] = self.values[(locale, product)]
                        return self.cache[cache_key]
            ''')},
            {"policy.py": code('''
                def key(locale, product):
                    return "locale:" + locale + ":product:" + product
            '''), "catalog.py": code('''
                from policy import key

                class Catalog:
                    def __init__(self, values):
                        self.values = values
                        self.cache = {}

                    def label(self, locale, product):
                        cache_key = key(locale, product)
                        if cache_key not in self.cache:
                            self.cache[cache_key] = self.values[(locale, product)]
                        return self.cache[cache_key]
            ''')},
            '''
                import unittest
                from catalog import Catalog

                class Public(unittest.TestCase):
                    def test_locales_do_not_share_labels(self):
                        catalog = Catalog({("en", "save"): "Save", ("fr", "save"): "Enregistrer"})
                        self.assertEqual(catalog.label("en", "save"), "Save")
                        self.assertEqual(catalog.label("fr", "save"), "Enregistrer")
            ''',
            '''
                import unittest
                from catalog import Catalog

                class Hidden(unittest.TestCase):
                    def test_warm_cache_isolated_in_both_directions(self):
                        catalog = Catalog({("en", "open"): "Open", ("de", "open"): "Öffnen"})
                        self.assertEqual(catalog.label("de", "open"), "Öffnen")
                        self.assertEqual(catalog.label("en", "open"), "Open")
                        self.assertEqual(catalog.label("de", "open"), "Öffnen")
            ''') ,
        spec("canonical_audit_path", "cross-module", "An audit record stores an alias instead of the canonical resource path used for authorization.",
            {"resolver.py": code('''
                TARGETS = {"/shortcut": "/documents/secret"}

                def resolve(path):
                    return TARGETS.get(path, path)
            '''), "audit.py": code('''
                from resolver import resolve

                def record(user, path):
                    return {"user": user, "resource": path}

                def read_and_record(user, path):
                    resolved = resolve(path)
                    return resolved, record(user, path)
            ''')},
            {"resolver.py": code('''
                TARGETS = {"/shortcut": "/documents/secret"}

                def resolve(path):
                    return TARGETS.get(path, path)
            '''), "audit.py": code('''
                from resolver import resolve

                def record(user, path):
                    return {"user": user, "resource": path}

                def read_and_record(user, path):
                    resolved = resolve(path)
                    return resolved, record(user, resolved)
            ''')},
            '''
                import unittest
                from audit import read_and_record

                class Public(unittest.TestCase):
                    def test_alias_audit_uses_canonical_path(self):
                        _, event = read_and_record("alice", "/shortcut")
                        self.assertEqual(event["resource"], "/documents/secret")
            ''',
            '''
                import unittest
                from audit import read_and_record

                class Hidden(unittest.TestCase):
                    def test_direct_and_alias_events_are_canonical(self):
                        _, alias_event = read_and_record("alice", "/shortcut")
                        _, direct_event = read_and_record("alice", "/documents/secret")
                        self.assertEqual(alias_event, direct_event)
            ''') ,
        spec("feature_rollout_scope", "cross-module", "A feature assignment key ignores tenant scope and gives one tenant another tenant's rollout decision.",
            {"rules.py": code('''
                ENABLED = {("acme", "alice")}

                def enabled(tenant, user):
                    return user == "alice"
            '''), "assign.py": code('''
                from rules import enabled

                def visible(tenant, user):
                    return enabled(tenant, user)
            ''')},
            {"rules.py": code('''
                ENABLED = {("acme", "alice")}

                def enabled(tenant, user):
                    return (tenant, user) in ENABLED
            '''), "assign.py": code('''
                from rules import enabled

                def visible(tenant, user):
                    return enabled(tenant, user)
            ''')},
            '''
                import unittest
                from assign import visible

                class Public(unittest.TestCase):
                    def test_assignment_is_tenant_scoped(self):
                        self.assertTrue(visible("acme", "alice"))
                        self.assertFalse(visible("globex", "alice"))
            ''',
            '''
                import unittest
                from assign import visible

                class Hidden(unittest.TestCase):
                    def test_same_user_can_differ_by_tenant(self):
                        self.assertTrue(visible("acme", "alice"))
                        self.assertFalse(visible("globex", "alice"))
                        self.assertFalse(visible("acme", "bob"))
            ''') ,
        spec("snapshot_revision_gate", "cross-module", "A state store accepts an older snapshot after a newer revision has been published.",
            {"state.py": code('''
                class Store:
                    def __init__(self):
                        self.revision = 0
                        self.value = {}

                    def publish(self, revision, value):
                        self.revision = revision
                        self.value = dict(value)

                    def read(self):
                        return self.revision, dict(self.value)
            '''), "view.py": code('''
                from state import Store

                def refresh(store, revision, value):
                    store.publish(revision, value)
                    return store.read()
            ''')},
            {"state.py": code('''
                class Store:
                    def __init__(self):
                        self.revision = 0
                        self.value = {}

                    def publish(self, revision, value):
                        if revision <= self.revision:
                            return False
                        self.revision = revision
                        self.value = dict(value)
                        return True

                    def read(self):
                        return self.revision, dict(self.value)
            '''), "view.py": code('''
                from state import Store

                def refresh(store, revision, value):
                    store.publish(revision, value)
                    return store.read()
            ''')},
            '''
                import unittest
                from state import Store
                from view import refresh

                class Public(unittest.TestCase):
                    def test_newer_revision_wins(self):
                        store = Store()
                        self.assertEqual(refresh(store, 2, {"mode": "new"}), (2, {"mode": "new"}))
                        self.assertEqual(refresh(store, 1, {"mode": "old"}), (2, {"mode": "new"}))
            ''',
            '''
                import unittest
                from state import Store
                from view import refresh

                class Hidden(unittest.TestCase):
                    def test_duplicate_and_stale_revisions_do_not_replace_state(self):
                        store = Store()
                        refresh(store, 4, {"count": 4})
                        self.assertEqual(refresh(store, 4, {"count": 44}), (4, {"count": 4}))
                        self.assertEqual(refresh(store, 3, {"count": 3}), (4, {"count": 4}))
            ''') ,
        spec("header_precedence", "cross-module", "A loader lets an environment value override an explicit command-line setting.",
            {"config.py": code('''
                def choose(cli, env, file_value):
                    return env or cli or file_value or "production"
            '''), "loader.py": code('''
                from config import choose

                def load(cli, env, file_value):
                    return choose(cli, env, file_value)
            ''')},
            {"config.py": code('''
                def choose(cli, env, file_value):
                    if cli is not None:
                        return cli
                    if env is not None:
                        return env
                    return file_value if file_value is not None else "production"
            '''), "loader.py": code('''
                from config import choose

                def load(cli, env, file_value):
                    return choose(cli, env, file_value)
            ''')},
            '''
                import unittest
                from loader import load

                class Public(unittest.TestCase):
                    def test_explicit_cli_wins(self):
                        self.assertEqual(load("debug", "production", "file"), "debug")
            ''',
            '''
                import unittest
                from loader import load

                class Hidden(unittest.TestCase):
                    def test_precedence_and_falsey_values(self):
                        self.assertEqual(load("", "env", "file"), "")
                        self.assertEqual(load(None, "env", "file"), "env")
                        self.assertEqual(load(None, None, "file"), "file")
            ''') ,
        spec("filter_before_limit", "cross-module", "A repository applies pagination before filtering and drops matching records beyond the first page.",
            {"filters.py": code('''
                def matches(row, status):
                    return status is None or row["status"] == status
            '''), "repository.py": code('''
                from filters import matches

                def query(rows, status=None, limit=10):
                    return [row for row in rows[:limit] if matches(row, status)]
            ''')},
            {"filters.py": code('''
                def matches(row, status):
                    return status is None or row["status"] == status
            '''), "repository.py": code('''
                from filters import matches

                def query(rows, status=None, limit=10):
                    filtered = [row for row in rows if matches(row, status)]
                    return filtered[:limit]
            ''')},
            '''
                import unittest
                from repository import query

                class Public(unittest.TestCase):
                    def test_filter_is_applied_before_limit(self):
                        rows = [{"id": 1, "status": "closed"}, {"id": 2, "status": "open"}]
                        self.assertEqual(query(rows, "open", 1), [{"id": 2, "status": "open"}])
            ''',
            '''
                import unittest
                from repository import query

                class Hidden(unittest.TestCase):
                    def test_limit_is_on_matching_rows_and_none_keeps_all(self):
                        rows = [{"id": 1, "status": "closed"}, {"id": 2, "status": "open"}, {"id": 3, "status": "open"}]
                        self.assertEqual([row["id"] for row in query(rows, "open", 1)], [2])
                        self.assertEqual([row["id"] for row in query(rows, None, 2)], [1, 2])
            ''') ,
        spec("versioned_event_default", "cross-module", "An event consumer treats a missing version as the newest schema and skips the compatibility parser.",
            {"events.py": code('''
                def version(event):
                    return event.get("version", 2)
            '''), "consumer.py": code('''
                from events import version

                def decode(event):
                    current = version(event)
                    if current == 1:
                        return {"name": event["name"], "active": bool(event["enabled"])}
                    return {"name": event["name"], "active": event["active"]}
            ''')},
            {"events.py": code('''
                def version(event):
                    return event.get("version", 1)
            '''), "consumer.py": code('''
                from events import version

                def decode(event):
                    current = version(event)
                    if current == 1:
                        return {"name": event["name"], "active": bool(event["enabled"])}
                    if current == 2:
                        return {"name": event["name"], "active": bool(event["active"])}
                    raise ValueError("unsupported version")
            ''')},
            '''
                import unittest
                from consumer import decode

                class Public(unittest.TestCase):
                    def test_missing_version_uses_legacy_shape(self):
                        self.assertEqual(decode({"name": "x", "enabled": 1}), {"name": "x", "active": True})
            ''',
            '''
                import unittest
                from consumer import decode

                class Hidden(unittest.TestCase):
                    def test_versions_and_unknown_schema(self):
                        self.assertEqual(decode({"name": "x", "enabled": 0}), {"name": "x", "active": False})
                        self.assertEqual(decode({"version": 2, "name": "x", "active": 1}), {"name": "x", "active": True})
                        with self.assertRaises(ValueError):
                            decode({"version": 9, "name": "x"})
            ''') ,
        spec("cache_invalidation_scope", "cross-module", "A cache invalidator clears an entity globally instead of only within the requested tenant.",
            {"cache.py": code('''
                class Cache:
                    def __init__(self):
                        self.values = {}

                    def put(self, tenant, entity, value):
                        self.values[(tenant, entity)] = value

                    def invalidate(self, tenant, entity):
                        for key in list(self.values):
                            if key[1] == entity:
                                del self.values[key]

                    def get(self, tenant, entity):
                        return self.values.get((tenant, entity))
            '''), "service.py": code('''
                from cache import Cache

                def remove(cache, tenant, entity):
                    cache.invalidate(tenant, entity)
                    return cache.get(tenant, entity)
            ''')},
            {"cache.py": code('''
                class Cache:
                    def __init__(self):
                        self.values = {}

                    def put(self, tenant, entity, value):
                        self.values[(tenant, entity)] = value

                    def invalidate(self, tenant, entity):
                        self.values.pop((tenant, entity), None)

                    def get(self, tenant, entity):
                        return self.values.get((tenant, entity))
            '''), "service.py": code('''
                from cache import Cache

                def remove(cache, tenant, entity):
                    cache.invalidate(tenant, entity)
                    return cache.get(tenant, entity)
            ''')},
            '''
                import unittest
                from cache import Cache
                from service import remove

                class Public(unittest.TestCase):
                    def test_invalidation_is_tenant_scoped(self):
                        cache = Cache()
                        cache.put("a", "profile", "A")
                        cache.put("b", "profile", "B")
                        self.assertIsNone(remove(cache, "a", "profile"))
                        self.assertEqual(cache.get("b", "profile"), "B")
            ''',
            '''
                import unittest
                from cache import Cache
                from service import remove

                class Hidden(unittest.TestCase):
                    def test_other_entities_and_tenants_survive(self):
                        cache = Cache()
                        cache.put("a", "profile", "A")
                        cache.put("a", "settings", "S")
                        cache.put("b", "profile", "B")
                        remove(cache, "a", "profile")
                        self.assertEqual(cache.get("a", "settings"), "S")
                        self.assertEqual(cache.get("b", "profile"), "B")
            ''') ,
        spec("outbox_acceptance", "integration", "A worker acknowledges a provider write before recording the durable local outcome.",
            {"store.py": code('''
                class Store:
                    def __init__(self):
                        self.events = []

                    def append(self, event):
                        self.events.append(dict(event))
            '''), "worker.py": code('''
                def handle(event, provider, store):
                    provider.send(event)
                    return "ack"
            ''')},
            {"store.py": code('''
                class Store:
                    def __init__(self):
                        self.events = []

                    def append(self, event):
                        self.events.append(dict(event))
            '''), "worker.py": code('''
                def handle(event, provider, store):
                    try:
                        provider.send(event)
                    except TimeoutError:
                        return "pending"
                    store.append(event)
                    return "ack"
            ''')},
            '''
                import unittest
                from store import Store
                from worker import handle

                class Provider:
                    def send(self, event):
                        return "sent"

                class Public(unittest.TestCase):
                    def test_ack_has_durable_record(self):
                        store = Store()
                        self.assertEqual(handle({"id": "e1"}, Provider(), store), "ack")
                        self.assertEqual(store.events, [{"id": "e1"}])
            ''',
            '''
                import unittest
                from store import Store
                from worker import handle

                class AcceptedThenTimeout:
                    def send(self, event):
                        raise TimeoutError("provider result unknown")

                class PublicProvider:
                    def send(self, event):
                        return "sent"

                class Hidden(unittest.TestCase):
                    def test_unknown_result_is_pending_and_not_ack(self):
                        store = Store()
                        self.assertEqual(handle({"id": "e2"}, AcceptedThenTimeout(), store), "pending")
                        self.assertEqual(store.events, [])
                        self.assertEqual(handle({"id": "e3"}, PublicProvider(), store), "ack")
                        self.assertEqual(store.events, [{"id": "e3"}])
            ''') ,
        spec("retry_global_budget", "integration", "A worker resets its deadline for every dependency and exceeds the declared total budget.",
            {"clock.py": code('''
                class Clock:
                    def __init__(self):
                        self.time = 0

                    def now(self):
                        return self.time

                    def advance(self, seconds):
                        self.time += seconds
            '''), "worker.py": code('''
                def run(dependencies, clock, budget):
                    for dependency in dependencies:
                        deadline = clock.now() + budget
                        dependency(clock, deadline)
                    return "ok"
            ''')},
            {"clock.py": code('''
                class Clock:
                    def __init__(self):
                        self.time = 0

                    def now(self):
                        return self.time

                    def advance(self, seconds):
                        self.time += seconds
            '''), "worker.py": code('''
                def run(dependencies, clock, budget):
                    deadline = clock.now() + budget
                    for dependency in dependencies:
                        if clock.now() >= deadline:
                            raise TimeoutError("budget exhausted")
                        dependency(clock, deadline)
                    return "ok"
            ''')},
            '''
                import unittest
                from clock import Clock
                from worker import run

                def slow(clock, deadline):
                    clock.advance(3)
                    if clock.now() > deadline:
                        raise TimeoutError("dependency deadline")

                class Public(unittest.TestCase):
                    def test_one_global_budget(self):
                        with self.assertRaises(TimeoutError):
                            run([slow, slow], Clock(), 5)
            ''',
            '''
                import unittest
                from clock import Clock
                from worker import run

                def one(clock, deadline):
                    clock.advance(2)
                    if clock.now() > deadline:
                        raise TimeoutError("dependency deadline")

                def two(clock, deadline):
                    clock.advance(2)
                    if clock.now() > deadline:
                        raise TimeoutError("dependency deadline")

                class Hidden(unittest.TestCase):
                    def test_budget_is_shared_and_exact_boundary_is_allowed(self):
                        with self.assertRaises(TimeoutError):
                            run([one, two, one], Clock(), 5)
                        self.assertEqual(run([one, two], Clock(), 4), "ok")
            ''') ,
        spec("quota_failure_release", "integration", "A failed checkout leaves a reservation consumed instead of releasing it.",
            {"quota.py": code('''
                class Quota:
                    def __init__(self, available):
                        self.available = available

                    def reserve(self, amount):
                        if amount > self.available:
                            raise ValueError("quota")
                        self.available -= amount

                    def release(self, amount):
                        self.available += amount
            '''), "checkout.py": code('''
                def purchase(quota, payment, amount):
                    quota.reserve(amount)
                    try:
                        payment(amount)
                    except Exception:
                        return "failed"
                    return "paid"
            ''')},
            {"quota.py": code('''
                class Quota:
                    def __init__(self, available):
                        self.available = available

                    def reserve(self, amount):
                        if amount > self.available:
                            raise ValueError("quota")
                        self.available -= amount

                    def release(self, amount):
                        self.available += amount
            '''), "checkout.py": code('''
                def purchase(quota, payment, amount):
                    quota.reserve(amount)
                    try:
                        payment(amount)
                    except Exception:
                        quota.release(amount)
                        return "failed"
                    return "paid"
            ''')},
            '''
                import unittest
                from checkout import purchase
                from quota import Quota

                def declines(amount):
                    raise RuntimeError("declined")

                class Public(unittest.TestCase):
                    def test_failed_payment_restores_quota(self):
                        quota = Quota(10)
                        self.assertEqual(purchase(quota, declines, 4), "failed")
                        self.assertEqual(quota.available, 10)
            ''',
            '''
                import unittest
                from checkout import purchase
                from quota import Quota

                def declines(amount):
                    raise RuntimeError("declined")

                def accepts(amount):
                    return "ok"

                class Hidden(unittest.TestCase):
                    def test_failure_release_and_success_consumption(self):
                        quota = Quota(10)
                        self.assertEqual(purchase(quota, declines, 4), "failed")
                        self.assertEqual(quota.available, 10)
                        self.assertEqual(purchase(quota, accepts, 6), "paid")
                        self.assertEqual(quota.available, 4)
            ''') ,
        spec("batch_payload_identity", "integration", "A batch ledger deduplicates by event ID and reuses a result for a changed payload.",
            {"ledger.py": code('''
                class Ledger:
                    def __init__(self):
                        self.records = {}

                    def key(self, event):
                        return event["event_id"]

                    def find(self, event):
                        return self.records.get(self.key(event))

                    def save(self, event, result):
                        self.records[self.key(event)] = result
            '''), "batch.py": code('''
                def deliver(ledger, event, send):
                    prior = ledger.find(event)
                    if prior is not None:
                        return prior
                    result = send(event)
                    ledger.save(event, result)
                    return result
            ''')},
            {"ledger.py": code('''
                import hashlib

                class Ledger:
                    def __init__(self):
                        self.records = {}

                    def key(self, event):
                        payload = event["payload"].encode("utf-8")
                        return (event["event_id"], hashlib.sha256(payload).hexdigest())

                    def find(self, event):
                        return self.records.get(self.key(event))

                    def save(self, event, result):
                        self.records[self.key(event)] = result
            '''), "batch.py": code('''
                def deliver(ledger, event, send):
                    prior = ledger.find(event)
                    if prior is not None:
                        return prior
                    result = send(event)
                    ledger.save(event, result)
                    return result
            ''')},
            '''
                import unittest
                from batch import deliver
                from ledger import Ledger

                class Public(unittest.TestCase):
                    def test_changed_payload_is_a_new_operation(self):
                        calls = []
                        def send(event):
                            calls.append(event["payload"])
                            return event["payload"]
                        ledger = Ledger()
                        self.assertEqual(deliver(ledger, {"event_id": "e", "payload": "one"}, send), "one")
                        self.assertEqual(deliver(ledger, {"event_id": "e", "payload": "two"}, send), "two")
                        self.assertEqual(calls, ["one", "two"])
            ''',
            '''
                import unittest
                from batch import deliver
                from ledger import Ledger

                class Hidden(unittest.TestCase):
                    def test_exact_duplicate_only_is_reused(self):
                        calls = []
                        def send(event):
                            calls.append(event["payload"])
                            return len(calls)
                        ledger = Ledger()
                        event = {"event_id": "e", "payload": "same"}
                        self.assertEqual(deliver(ledger, event, send), 1)
                        self.assertEqual(deliver(ledger, dict(event), send), 1)
                        self.assertEqual(deliver(ledger, {"event_id": "e", "payload": "other"}, send), 2)
                        self.assertEqual(calls, ["same", "other"])
            ''') ,
        spec("monotonic_revision", "integration", "A consumer applies an out-of-order update and regresses the authoritative value.",
            {"store.py": code('''
                class Store:
                    def __init__(self):
                        self.revision = 0
                        self.value = None

                    def apply(self, revision, value):
                        self.revision = revision
                        self.value = value

                    def read(self):
                        return self.revision, self.value
            '''), "consumer.py": code('''
                from store import Store

                def consume(store, events):
                    for event in events:
                        store.apply(event["revision"], event["value"])
                    return store.read()
            ''')},
            {"store.py": code('''
                class Store:
                    def __init__(self):
                        self.revision = 0
                        self.value = None

                    def apply(self, revision, value):
                        if revision <= self.revision:
                            return False
                        self.revision = revision
                        self.value = value
                        return True

                    def read(self):
                        return self.revision, self.value
            '''), "consumer.py": code('''
                from store import Store

                def consume(store, events):
                    for event in events:
                        store.apply(event["revision"], event["value"])
                    return store.read()
            ''')},
            '''
                import unittest
                from consumer import consume
                from store import Store

                class Public(unittest.TestCase):
                    def test_stale_update_is_ignored(self):
                        events = [{"revision": 2, "value": "new"}, {"revision": 1, "value": "old"}]
                        self.assertEqual(consume(Store(), events), (2, "new"))
            ''',
            '''
                import unittest
                from consumer import consume
                from store import Store

                class Hidden(unittest.TestCase):
                    def test_duplicate_and_stale_updates_are_ignored(self):
                        events = [{"revision": 3, "value": "x"}, {"revision": 3, "value": "wrong"}, {"revision": 2, "value": "old"}]
                        self.assertEqual(consume(Store(), events), (3, "x"))
            ''') ,
        spec("lease_owner_expiry", "integration", "A lease renewal extends a lock even when the caller is no longer its owner.",
            {"lease.py": code('''
                class Lease:
                    def __init__(self):
                        self.owner = None
                        self.expires = 0

                    def acquire(self, owner, now, ttl):
                        if self.owner is not None and now < self.expires:
                            return False
                        self.owner = owner
                        self.expires = now + ttl
                        return True

                    def renew(self, owner, now, ttl):
                        self.expires = now + ttl
                        return True
            '''), "worker.py": code('''
                from lease import Lease

                def heartbeat(lease, owner, now, ttl):
                    return lease.renew(owner, now, ttl)
            ''')},
            {"lease.py": code('''
                class Lease:
                    def __init__(self):
                        self.owner = None
                        self.expires = 0

                    def acquire(self, owner, now, ttl):
                        if self.owner is not None and now < self.expires:
                            return False
                        self.owner = owner
                        self.expires = now + ttl
                        return True

                    def renew(self, owner, now, ttl):
                        if self.owner != owner or now >= self.expires:
                            raise PermissionError("lease not owned")
                        self.expires = now + ttl
                        return True
            '''), "worker.py": code('''
                from lease import Lease

                def heartbeat(lease, owner, now, ttl):
                    return lease.renew(owner, now, ttl)
            ''')},
            '''
                import unittest
                from lease import Lease
                from worker import heartbeat

                class Public(unittest.TestCase):
                    def test_only_owner_can_renew(self):
                        lease = Lease()
                        self.assertTrue(lease.acquire("alice", 0, 10))
                        with self.assertRaises(PermissionError):
                            heartbeat(lease, "bob", 1, 10)
            ''',
            '''
                import unittest
                from lease import Lease
                from worker import heartbeat

                class Hidden(unittest.TestCase):
                    def test_owner_and_expiry_boundaries(self):
                        lease = Lease()
                        self.assertTrue(lease.acquire("alice", 0, 10))
                        self.assertTrue(heartbeat(lease, "alice", 5, 10))
                        with self.assertRaises(PermissionError):
                            heartbeat(lease, "bob", 6, 10)
                        lease.expires = 6
                        with self.assertRaises(PermissionError):
                            heartbeat(lease, "alice", 6, 10)
            ''') ,
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def write_tree(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(content, encoding="utf-8")


def materialize(corpus: Path) -> dict[str, object]:
    tasks = make_tasks()
    if len(tasks) != 20 or len({task.task_id for task in tasks}) != 20:
        raise ValueError("v7 corpus must contain 20 unique tasks")
    if corpus.exists():
        raise FileExistsError(f"refusing to overwrite existing corpus: {corpus}")
    manifest_tasks: list[dict[str, object]] = []
    for task in tasks:
        public_root = corpus / "tasks" / task.task_id
        hidden_root = corpus / "hidden" / task.task_id
        write_tree(public_root, task.source | {"task.md": task.description, "tests/test_public.py": task.public_test})
        write_tree(hidden_root, task.fixed | {"task.md": task.description, "tests/test_hidden.py": task.hidden_test})
        manifest_tasks.append({
            "task_id": task.task_id,
            "stratum": task.stratum,
            "workspace_path": f"tasks/{task.task_id}",
            "hidden_root_path": f"hidden/{task.task_id}",
            "allowed_edit_paths": sorted(task.source),
            "causal_owner_candidates": sorted(task.source),
            "public_command": PUBLIC_COMMAND,
            "hidden_command": PUBLIC_COMMAND,
            "workspace_tree_sha256": tree_digest(public_root),
            "hidden_tree_sha256": tree_digest(hidden_root),
        })
    manifest = cast(dict[str, object], {
        "schema_version": 1,
        "corpus_id": "effect-corpus-v7",
        "generated_by": "scripts/materialize_effect_corpus_v7.py",
        "task_count": len(tasks),
        "strata": {"single-module": 6, "cross-module": 8, "integration": 6},
        "split": {
            "public_workspace_excludes_hidden_tests": True,
            "hidden_tests_are_injected_after_agent_exit": True,
            "references_and_expected_repairs_are_scorer_only": True,
        },
        "tasks": manifest_tasks,
    })
    corpus.mkdir(parents=True, exist_ok=True)
    _ = (corpus / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", type=Path, required=True)
    args = parser.parse_args()
    _ = materialize(cast(Path, args.corpus))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
