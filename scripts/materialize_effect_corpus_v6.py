#!/usr/bin/env python3
"""Materialize a fresh multi-file causal-repair corpus without external dependencies."""

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
        spec(
            "tenant_cache_identity", "cross-module",
            "A catalog sometimes returns another tenant's price after a warm cache. Preserve per-tenant price ownership and cache isolation.",
            {
                "policy.py": code('''
                    def cache_key(tenant, sku):
                        return f"sku:{sku}"
                '''),
                "catalog.py": code('''
                    from policy import cache_key

                    class Catalog:
                        def __init__(self, prices):
                            self.prices = prices
                            self.cache = {}

                        def price(self, tenant, sku):
                            key = cache_key(tenant, sku)
                            if key not in self.cache:
                                self.cache[key] = self.prices[(tenant, sku)]
                            return self.cache[key]
                '''),
            },
            {
                "policy.py": code('''
                    def cache_key(tenant, sku):
                        return f"tenant:{tenant}:sku:{sku}"
                '''),
                "catalog.py": code('''
                    from policy import cache_key

                    class Catalog:
                        def __init__(self, prices):
                            self.prices = prices
                            self.cache = {}

                        def price(self, tenant, sku):
                            key = cache_key(tenant, sku)
                            if key not in self.cache:
                                self.cache[key] = self.prices[(tenant, sku)]
                            return self.cache[key]
                '''),
            },
            '''
                import unittest
                from catalog import Catalog

                class Public(unittest.TestCase):
                    def test_same_tenant_cache(self):
                        catalog = Catalog({("acme", "basic"): 10, ("globex", "basic"): 90})
                        self.assertEqual(catalog.price("acme", "basic"), 10)
                        self.assertEqual(catalog.price("globex", "basic"), 90)
            ''',
            '''
                import unittest
                from catalog import Catalog

                class Hidden(unittest.TestCase):
                    def test_tenants_never_share_prices(self):
                        catalog = Catalog({("acme", "basic"): 10, ("globex", "basic"): 90})
                        self.assertEqual(catalog.price("acme", "basic"), 10)
                        self.assertEqual(catalog.price("globex", "basic"), 90)
            ''',
        ),
        spec(
            "permission_target_resolution", "cross-module",
            "An alias read is authorized inconsistently with its resolved target. Preserve authorization on the canonical resource.",
            {
                "policy.py": code('''
                    ACL = {"public": {"alice"}, "secret": {"admin"}}

                    def allowed(user, resource):
                        return user in ACL.get(resource, set())
                '''),
                "resource_service.py": code('''
                    from policy import allowed

                    TARGETS = {"alias": "secret"}
                    DATA = {"public": "hello", "secret": "classified"}

                    def resolve(path):
                        return TARGETS.get(path, path)

                    def read(user, path):
                        target = resolve(path)
                        if not allowed(user, path):
                            raise PermissionError("forbidden")
                        return DATA[target]
                '''),
            },
            {
                "policy.py": code('''
                    ACL = {"public": {"alice"}, "secret": {"admin"}}

                    def allowed(user, resource):
                        return user in ACL.get(resource, set())
                '''),
                "resource_service.py": code('''
                    from policy import allowed

                    TARGETS = {"alias": "secret"}
                    DATA = {"public": "hello", "secret": "classified"}

                    def resolve(path):
                        return TARGETS.get(path, path)

                    def read(user, path):
                        target = resolve(path)
                        if not allowed(user, target):
                            raise PermissionError("forbidden")
                        return DATA[target]
                '''),
            },
            '''
                import unittest
                from resource_service import read

                class Public(unittest.TestCase):
                    def test_public_resource(self):
                        self.assertEqual(read("alice", "public"), "hello")
                        self.assertEqual(read("admin", "alias"), "classified")
            ''',
            '''
                import unittest
                from resource_service import read

                class Hidden(unittest.TestCase):
                    def test_alias_uses_canonical_authorization(self):
                        with self.assertRaises(PermissionError):
                            read("alice", "alias")
                        self.assertEqual(read("admin", "alias"), "classified")
            ''',
        ),
        spec(
            "unknown_write_reconciliation", "integration",
            "A delivery worker retries an ambiguous provider timeout. Preserve pending state until reconciliation distinguishes accepted, absent, or retryable pre-acceptance work.",
            {
                "provider.py": code('''
                    class RetryablePreAcceptance(Exception):
                        pass

                    class Provider:
                        def __init__(self, mode):
                            self.mode = mode
                            self.calls = 0
                            self.accepted = []

                        def send(self, operation):
                            self.calls += 1
                            if self.mode == "retryable" and self.calls == 1:
                                raise RetryablePreAcceptance()
                            self.accepted.append(operation["id"])
                            if self.mode == "accepted-timeout" and self.calls == 1:
                                raise TimeoutError()
                            return "sent"

                        def reconcile(self, operation):
                            return "FOUND" if operation["id"] in self.accepted else "ABSENT"
                '''),
                "dispatcher.py": code('''
                    from provider import RetryablePreAcceptance

                    class Dispatcher:
                        def __init__(self, provider):
                            self.provider = provider

                        def deliver(self, operation):
                            try:
                                return self.provider.send(operation)
                            except RetryablePreAcceptance:
                                return self.deliver(operation)
                            except TimeoutError:
                                return self.deliver(operation)
                '''),
            },
            {
                "provider.py": code('''
                    class RetryablePreAcceptance(Exception):
                        pass

                    class Provider:
                        def __init__(self, mode):
                            self.mode = mode
                            self.calls = 0
                            self.accepted = []

                        def send(self, operation):
                            self.calls += 1
                            if self.mode == "retryable" and self.calls == 1:
                                raise RetryablePreAcceptance()
                            self.accepted.append(operation["id"])
                            if self.mode == "accepted-timeout" and self.calls == 1:
                                raise TimeoutError()
                            return "sent"

                        def reconcile(self, operation):
                            return "FOUND" if operation["id"] in self.accepted else "ABSENT"
                '''),
                "dispatcher.py": code('''
                    from provider import RetryablePreAcceptance

                    class Dispatcher:
                        def __init__(self, provider):
                            self.provider = provider

                        def deliver(self, operation):
                            try:
                                return self.provider.send(operation)
                            except RetryablePreAcceptance:
                                return self.deliver(operation)
                            except TimeoutError:
                                return "pending"
                '''),
            },
            '''
                import unittest
                from dispatcher import Dispatcher
                from provider import Provider

                class Public(unittest.TestCase):
                    def test_pre_acceptance_rejection_can_retry(self):
                        provider = Provider("accepted-timeout")
                        self.assertEqual(Dispatcher(provider).deliver({"id": "op-1"}), "pending")
                        self.assertEqual(provider.accepted, ["op-1"])
            ''',
            '''
                import unittest
                from dispatcher import Dispatcher
                from provider import Provider

                class Hidden(unittest.TestCase):
                    def test_accepted_timeout_stays_pending_without_duplicate(self):
                        provider = Provider("accepted-timeout")
                        self.assertEqual(Dispatcher(provider).deliver({"id": "op-9"}), "pending")
                        self.assertEqual(provider.accepted, ["op-9"])
            ''',
        ),
        spec(
            "operation_identity_dimensions", "integration",
            "A sender reuses a prior remote result when only the business event ID matches. Preserve the full side-effect identity.",
            {
                "ledger.py": code('''
                    class Ledger:
                        def __init__(self):
                            self.records = {}

                        def key(self, operation):
                            return operation["event_id"]

                        def find(self, operation):
                            return self.records.get(self.key(operation))

                        def save(self, operation, result):
                            self.records[self.key(operation)] = result
                '''),
                "sender.py": code('''
                    class Sender:
                        def __init__(self, ledger):
                            self.ledger = ledger
                            self.sent = []

                        def send(self, operation):
                            prior = self.ledger.find(operation)
                            if prior is not None:
                                return prior
                            result = {"amount": operation["amount"], "tenant": operation["tenant"]}
                            self.sent.append(operation.copy())
                            self.ledger.save(operation, result)
                            return result
                '''),
            },
            {
                "ledger.py": code('''
                    class Ledger:
                        def __init__(self):
                            self.records = {}

                        def key(self, operation):
                            return (operation["event_id"], operation["tenant"], operation["recipient"], operation["amount"], operation["version"])

                        def find(self, operation):
                            return self.records.get(self.key(operation))

                        def save(self, operation, result):
                            self.records[self.key(operation)] = result
                '''),
                "sender.py": code('''
                    class Sender:
                        def __init__(self, ledger):
                            self.ledger = ledger
                            self.sent = []

                        def send(self, operation):
                            prior = self.ledger.find(operation)
                            if prior is not None:
                                return prior
                            result = {"amount": operation["amount"], "tenant": operation["tenant"]}
                            self.sent.append(operation.copy())
                            self.ledger.save(operation, result)
                            return result
                '''),
            },
            '''
                import unittest
                from ledger import Ledger
                from sender import Sender

                class Public(unittest.TestCase):
                    def test_exact_duplicate_is_deduplicated(self):
                        sender = Sender(Ledger())
                        operation = {"event_id": "e1", "tenant": "a", "recipient": "r", "amount": 5, "version": 1}
                        changed = {"event_id": "e1", "tenant": "a", "recipient": "r", "amount": 6, "version": 1}
                        sender.send(operation)
                        sender.send(changed)
                        self.assertEqual(len(sender.sent), 2)
            ''',
            '''
                import unittest
                from ledger import Ledger
                from sender import Sender

                class Hidden(unittest.TestCase):
                    def test_event_id_alone_is_not_identity(self):
                        sender = Sender(Ledger())
                        first = {"event_id": "e1", "tenant": "a", "recipient": "r", "amount": 5, "version": 1}
                        second = {"event_id": "e1", "tenant": "b", "recipient": "r", "amount": 7, "version": 1}
                        sender.send(first)
                        self.assertEqual(sender.send(second)["amount"], 7)
                        self.assertEqual(len(sender.sent), 2)
            ''',
        ),
        spec(
            "configuration_precedence", "single-module",
            "A runtime mode ignores a higher-precedence environment override. Preserve explicit configuration precedence and a stable default.",
            {
                "config.py": code('''
                    import os

                    def mode(file_value=None, default="safe"):
                        return file_value if file_value is not None else default
                '''),
            },
            {
                "config.py": code('''
                    import os

                    def mode(file_value=None, default="safe"):
                        environment_value = os.environ.get("APP_MODE")
                        return environment_value if environment_value is not None else (file_value if file_value is not None else default)
                '''),
            },
            '''
                import os
                import unittest
                from config import mode

                class Public(unittest.TestCase):
                    def test_file_value_without_environment(self):
                        old = os.environ.get("APP_MODE")
                        os.environ["APP_MODE"] = "fast"
                        try:
                            self.assertEqual(mode("balanced"), "fast")
                        finally:
                            if old is None:
                                os.environ.pop("APP_MODE", None)
                            else:
                                os.environ["APP_MODE"] = old
            ''',
            '''
                import os
                import unittest
                from config import mode

                class Hidden(unittest.TestCase):
                    def test_environment_precedes_file_value(self):
                        old = os.environ.get("APP_MODE")
                        os.environ["APP_MODE"] = "fast"
                        try:
                            self.assertEqual(mode("balanced"), "fast")
                        finally:
                            if old is None:
                                os.environ.pop("APP_MODE", None)
                            else:
                                os.environ["APP_MODE"] = old
            ''',
        ),
        spec(
            "snapshot_revision_invalidation", "cross-module",
            "A cached snapshot remains stale after its owner changes. Preserve an explicit revision transition between storage and cache.",
            {
                "store.py": code('''
                    class Store:
                        def __init__(self, value):
                            self.record = {"value": value, "version": 1}

                        def read(self):
                            return self.record.copy()

                        def update(self, value):
                            self.record["value"] = value
                '''),
                "snapshot.py": code('''
                    class Snapshot:
                        def __init__(self, store):
                            self.store = store
                            self.cache = {}

                        def read(self):
                            record = self.store.read()
                            key = "record"
                            if key not in self.cache:
                                self.cache[key] = record
                            return self.cache[key]["value"]
                '''),
            },
            {
                "store.py": code('''
                    class Store:
                        def __init__(self, value):
                            self.record = {"value": value, "version": 1}

                        def read(self):
                            return self.record.copy()

                        def update(self, value):
                            self.record["value"] = value
                            self.record["version"] += 1
                '''),
                "snapshot.py": code('''
                    class Snapshot:
                        def __init__(self, store):
                            self.store = store
                            self.cache = {}

                        def read(self):
                            record = self.store.read()
                            key = ("record", record["version"])
                            if key not in self.cache:
                                self.cache[key] = record
                            return self.cache[key]["value"]
                '''),
            },
            '''
                import unittest
                from snapshot import Snapshot
                from store import Store

                class Public(unittest.TestCase):
                    def test_initial_snapshot(self):
                        store = Store("old")
                        snapshot = Snapshot(store)
                        self.assertEqual(snapshot.read(), "old")
                        store.update("new")
                        self.assertEqual(snapshot.read(), "new")
            ''',
            '''
                import unittest
                from snapshot import Snapshot
                from store import Store

                class Hidden(unittest.TestCase):
                    def test_update_invalidates_snapshot(self):
                        store = Store("old")
                        snapshot = Snapshot(store)
                        self.assertEqual(snapshot.read(), "old")
                        store.update("new")
                        self.assertEqual(snapshot.read(), "new")
            ''',
        ),
        spec(
            "ack_after_durable_save", "integration",
            "A queue worker acknowledges before durable persistence. Preserve the state transition ordering on save failure.",
            {
                "inbox.py": code('''
                    class Inbox:
                        def __init__(self):
                            self.acknowledged = []

                        def ack(self, job_id):
                            self.acknowledged.append(job_id)

                    class Store:
                        def __init__(self, fail=False):
                            self.fail = fail
                            self.saved = []

                        def save(self, job):
                            if self.fail:
                                raise OSError("disk full")
                            self.saved.append(job)
                '''),
                "worker.py": code('''
                    class Worker:
                        def __init__(self, inbox, store):
                            self.inbox = inbox
                            self.store = store

                        def handle(self, job):
                            self.inbox.ack(job["id"])
                            self.store.save(job)
                            return "saved"
                '''),
            },
            {
                "inbox.py": code('''
                    class Inbox:
                        def __init__(self):
                            self.acknowledged = []

                        def ack(self, job_id):
                            self.acknowledged.append(job_id)

                    class Store:
                        def __init__(self, fail=False):
                            self.fail = fail
                            self.saved = []

                        def save(self, job):
                            if self.fail:
                                raise OSError("disk full")
                            self.saved.append(job)
                '''),
                "worker.py": code('''
                    class Worker:
                        def __init__(self, inbox, store):
                            self.inbox = inbox
                            self.store = store

                        def handle(self, job):
                            self.store.save(job)
                            self.inbox.ack(job["id"])
                            return "saved"
                '''),
            },
            '''
                import unittest
                from inbox import Inbox, Store
                from worker import Worker

                class Public(unittest.TestCase):
                    def test_success_is_saved_and_acked(self):
                        inbox, store = Inbox(), Store(fail=True)
                        with self.assertRaises(OSError):
                            Worker(inbox, store).handle({"id": "j1"})
                        self.assertEqual(inbox.acknowledged, [])
            ''',
            '''
                import unittest
                from inbox import Inbox, Store
                from worker import Worker

                class Hidden(unittest.TestCase):
                    def test_failed_save_is_not_acked(self):
                        inbox, store = Inbox(), Store(fail=True)
                        with self.assertRaises(OSError):
                            Worker(inbox, store).handle({"id": "j2"})
                        self.assertEqual(inbox.acknowledged, [])
            ''',
        ),
        spec(
            "half_open_pagination", "single-module",
            "A page endpoint includes the end cursor even though its contract is half-open. Preserve stable pagination boundaries.",
            {
                "pager.py": code('''
                    def page(items, start, end):
                        return items[start:end + 1]
                '''),
            },
            {
                "pager.py": code('''
                    def page(items, start, end):
                        return items[start:end]
                '''),
            },
            '''
                import unittest
                from pager import page

                class Public(unittest.TestCase):
                    def test_nonempty_page(self):
                        self.assertEqual(page(["a", "b", "c"], 0, 2), ["a", "b"])
            ''',
            '''
                import unittest
                from pager import page

                class Hidden(unittest.TestCase):
                    def test_empty_and_last_boundaries(self):
                        self.assertEqual(page(["a", "b", "c"], 1, 1), [])
                        self.assertEqual(page(["a", "b", "c"], 2, 3), ["c"])
            ''',
        ),
        spec(
            "tenant_rate_limit_scope", "cross-module",
            "A rate limit shared by two tenants undercounts isolation. Preserve tenant and user ownership in the admission key.",
            {
                "limiter.py": code('''
                    class Limiter:
                        def __init__(self, limit):
                            self.limit = limit
                            self.counts = {}

                        def allow(self, tenant, user):
                            key = user
                            count = self.counts.get(key, 0)
                            if count >= self.limit:
                                return False
                            self.counts[key] = count + 1
                            return True
                '''),
            },
            {
                "limiter.py": code('''
                    class Limiter:
                        def __init__(self, limit):
                            self.limit = limit
                            self.counts = {}

                        def allow(self, tenant, user):
                            key = (tenant, user)
                            count = self.counts.get(key, 0)
                            if count >= self.limit:
                                return False
                            self.counts[key] = count + 1
                            return True
                '''),
            },
            '''
                import unittest
                from limiter import Limiter

                class Public(unittest.TestCase):
                    def test_one_user_limit(self):
                        limiter = Limiter(1)
                        self.assertTrue(limiter.allow("acme", "u1"))
                        self.assertTrue(limiter.allow("globex", "u1"))
            ''',
            '''
                import unittest
                from limiter import Limiter

                class Hidden(unittest.TestCase):
                    def test_tenants_are_isolated(self):
                        limiter = Limiter(1)
                        self.assertTrue(limiter.allow("acme", "u1"))
                        self.assertTrue(limiter.allow("globex", "u1"))
            ''',
        ),
        spec(
            "money_rounding_owner", "integration",
            "An invoice rounds the subtotal before applying tax. Preserve monetary rounding at the final owner boundary.",
            {
                "billing.py": code('''
                    from decimal import Decimal, ROUND_HALF_UP

                    CENT = Decimal("0.01")

                    def total(items, tax_rate):
                        subtotal = sum(Decimal(str(price)) * Decimal(str(quantity)) for price, quantity in items)
                        rounded_subtotal = subtotal.quantize(CENT, rounding=ROUND_HALF_UP)
                        return (rounded_subtotal * (Decimal("1") + Decimal(str(tax_rate)))).quantize(CENT, rounding=ROUND_HALF_UP)
                '''),
            },
            {
                "billing.py": code('''
                    from decimal import Decimal, ROUND_HALF_UP

                    CENT = Decimal("0.01")

                    def total(items, tax_rate):
                        subtotal = sum(Decimal(str(price)) * Decimal(str(quantity)) for price, quantity in items)
                        return (subtotal * (Decimal("1") + Decimal(str(tax_rate)))).quantize(CENT, rounding=ROUND_HALF_UP)
                '''),
            },
            '''
                import unittest
                from billing import total

                class Public(unittest.TestCase):
                    def test_whole_cent_invoice(self):
                        self.assertEqual(str(total([("0.335", 1)], "0.05")), "0.35")
            ''',
            '''
                import unittest
                from billing import total

                class Hidden(unittest.TestCase):
                    def test_rounding_happens_after_tax(self):
                        self.assertEqual(total([("0.335", 1)], "0.10"), total([("0.335", 1)], "0.10"))
                        self.assertEqual(str(total([("0.335", 1)], "0.10")), "0.37")
            ''',
        ),
        spec(
            "role_cache_revision", "cross-module",
            "A role cache outlives a revoke operation. Preserve revision ownership when authorization state changes.",
            {
                "roles.py": code('''
                    class RoleStore:
                        def __init__(self):
                            self.values = {"alice": {"reader"}}
                            self.revision = 1

                        def roles(self, user):
                            return set(self.values.get(user, set()))

                        def revoke(self, user, role):
                            self.values[user].discard(role)
                            self.revision += 1

                    class Checker:
                        def __init__(self, store):
                            self.store = store
                            self.cache = {}

                        def has_role(self, user, role):
                            if user not in self.cache:
                                self.cache[user] = self.store.roles(user)
                            return role in self.cache[user]
                '''),
            },
            {
                "roles.py": code('''
                    class RoleStore:
                        def __init__(self):
                            self.values = {"alice": {"reader"}}
                            self.revision = 1

                        def roles(self, user):
                            return set(self.values.get(user, set()))

                        def revoke(self, user, role):
                            self.values[user].discard(role)
                            self.revision += 1

                    class Checker:
                        def __init__(self, store):
                            self.store = store
                            self.cache = {}

                        def has_role(self, user, role):
                            entry = self.cache.get(user)
                            if entry is None or entry[0] != self.store.revision:
                                entry = (self.store.revision, self.store.roles(user))
                                self.cache[user] = entry
                            return role in entry[1]
                '''),
            },
            '''
                import unittest
                from roles import Checker, RoleStore

                class Public(unittest.TestCase):
                    def test_granted_role(self):
                        store = RoleStore()
                        checker = Checker(store)
                        self.assertTrue(checker.has_role("alice", "reader"))
                        store.revoke("alice", "reader")
                        self.assertFalse(checker.has_role("alice", "reader"))
            ''',
            '''
                import unittest
                from roles import Checker, RoleStore

                class Hidden(unittest.TestCase):
                    def test_revoke_invalidates_cached_authority(self):
                        store = RoleStore()
                        checker = Checker(store)
                        self.assertTrue(checker.has_role("alice", "reader"))
                        store.revoke("alice", "reader")
                        self.assertFalse(checker.has_role("alice", "reader"))
            ''',
        ),
        spec(
            "event_missing_version", "single-module",
            "A legacy event without a version is parsed as the newest shape. Preserve the compatibility default at the parser boundary.",
            {
                "events.py": code('''
                    def parse(event):
                        version = event.get("version", 2)
                        if version == 1:
                            return {"name": event["name"]}
                        return {"name": event["payload"]["name"]}
                '''),
            },
            {
                "events.py": code('''
                    def parse(event):
                        version = event.get("version", 1)
                        if version == 1:
                            return {"name": event["name"]}
                        return {"name": event["payload"]["name"]}
                '''),
            },
            '''
                import unittest
                from events import parse

                class Public(unittest.TestCase):
                    def test_current_event(self):
                        self.assertEqual(parse({"version": 2, "payload": {"name": "Ada"}}), {"name": "Ada"})
                        self.assertEqual(parse({"name": "Grace"}), {"name": "Grace"})
            ''',
            '''
                import unittest
                from events import parse

                class Hidden(unittest.TestCase):
                    def test_missing_version_is_legacy(self):
                        self.assertEqual(parse({"name": "Grace"}), {"name": "Grace"})
            ''',
        ),
        spec(
            "global_retry_deadline", "integration",
            "A retry loop renews its deadline on every attempt. Preserve one caller-owned deadline across the whole operation.",
            {
                "retrying.py": code('''
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
                '''),
            },
            {
                "retrying.py": code('''
                    class Clock:
                        def __init__(self, values):
                            self.values = list(values)

                        def now(self):
                            return self.values.pop(0)

                    def run(work, clock, attempts=3, timeout=5):
                        deadline = clock.now() + timeout
                        for _ in range(attempts):
                            try:
                                return work()
                            except TimeoutError:
                                if clock.now() >= deadline:
                                    return "timed_out"
                        return "failed"
                '''),
            },
            '''
                import unittest
                from retrying import Clock, run

                class Public(unittest.TestCase):
                    def test_success_does_not_retry(self):
                        attempts = [0]

                        def work():
                            attempts[0] += 1
                            if attempts[0] < 3:
                                raise TimeoutError()
                            return "ok"

                        self.assertEqual(run(work, Clock([0, 4, 5, 6])), "timed_out")
            ''',
            '''
                import unittest
                from retrying import Clock, run

                class Hidden(unittest.TestCase):
                    def test_deadline_is_not_renewed(self):
                        attempts = [0]

                        def work():
                            attempts[0] += 1
                            if attempts[0] < 3:
                                raise TimeoutError()
                            return "ok"

                        self.assertEqual(run(work, Clock([0, 4, 5, 6, 7])), "timed_out")
                        self.assertEqual(attempts[0], 2)
            ''',
        ),
        spec(
            "tenant_record_ownership", "cross-module",
            "A record update checks existence but not tenant ownership. Preserve the authoritative tenant boundary at the state owner.",
            {
                "records.py": code('''
                    class Records:
                        def __init__(self):
                            self.rows = {"r1": {"tenant": "acme", "value": "old"}}

                        def update(self, tenant, record_id, value):
                            if record_id not in self.rows:
                                raise KeyError(record_id)
                            self.rows[record_id]["value"] = value
                            return self.rows[record_id]
                '''),
            },
            {
                "records.py": code('''
                    class Records:
                        def __init__(self):
                            self.rows = {"r1": {"tenant": "acme", "value": "old"}}

                        def update(self, tenant, record_id, value):
                            row = self.rows.get(record_id)
                            if row is None:
                                raise KeyError(record_id)
                            if row["tenant"] != tenant:
                                raise PermissionError("wrong tenant")
                            row["value"] = value
                            return row
                '''),
            },
            '''
                import unittest
                from records import Records

                class Public(unittest.TestCase):
                    def test_owner_can_update(self):
                        with self.assertRaises(PermissionError):
                            Records().update("globex", "r1", "stolen")
            ''',
            '''
                import unittest
                from records import Records

                class Hidden(unittest.TestCase):
                    def test_other_tenant_cannot_update(self):
                        with self.assertRaises(PermissionError):
                            Records().update("globex", "r1", "stolen")
            ''',
        ),
        spec(
            "terminal_job_lifecycle", "integration",
            "A terminal job rejection is treated as retryable and can be revived by redelivery. Preserve terminal state ownership.",
            {
                "jobs.py": code('''
                    class TerminalError(Exception):
                        pass

                    class TransientError(Exception):
                        pass

                    class Job:
                        def __init__(self, operation):
                            self.operation = operation
                            self.status = "pending"
                            self.attempts = 0

                        def process(self):
                            self.attempts += 1
                            try:
                                return self.operation()
                            except TerminalError:
                                return "retry"
                            except TransientError:
                                return "retry"
                '''),
            },
            {
                "jobs.py": code('''
                    class TerminalError(Exception):
                        pass

                    class TransientError(Exception):
                        pass

                    class Job:
                        def __init__(self, operation):
                            self.operation = operation
                            self.status = "pending"
                            self.attempts = 0

                        def process(self):
                            if self.status == "failed":
                                return "ignored"
                            self.attempts += 1
                            try:
                                result = self.operation()
                            except TerminalError:
                                self.status = "failed"
                                return "failed"
                            except TransientError:
                                return "retry"
                            self.status = "done"
                            return result
                '''),
            },
            '''
                import unittest
                from jobs import Job, TerminalError

                class Public(unittest.TestCase):
                    def test_success(self):
                        self.assertEqual(Job(lambda: (_ for _ in ()).throw(TerminalError())).process(), "failed")
            ''',
            '''
                import unittest
                from jobs import Job, TerminalError

                class Hidden(unittest.TestCase):
                    def test_terminal_rejection_is_durable(self):
                        job = Job(lambda: (_ for _ in ()).throw(TerminalError()))
                        self.assertEqual(job.process(), "failed")
                        self.assertEqual(job.process(), "ignored")
                        self.assertEqual(job.attempts, 1)
            ''',
        ),
        spec(
            "atomic_batch_commit", "integration",
            "A batch commit leaves partial rows before a retry. Preserve all-or-nothing state ownership across the batch transition.",
            {
                "batch.py": code('''
                    class Store:
                        def __init__(self, fail_at=None):
                            self.rows = []
                            self.fail_at = fail_at

                        def commit(self, rows):
                            for index, row in enumerate(rows):
                                if self.fail_at == index:
                                    raise OSError("transient write")
                                self.rows.append(row)

                    class Batch:
                        def __init__(self, store):
                            self.store = store

                        def process(self, rows):
                            try:
                                self.store.commit(rows)
                                return "ok"
                            except OSError:
                                return "retry"
                '''),
            },
            {
                "batch.py": code('''
                    class Store:
                        def __init__(self, fail_at=None):
                            self.rows = []
                            self.fail_at = fail_at

                        def commit(self, rows):
                            if self.fail_at is not None:
                                raise OSError("transient write")
                            self.rows.extend(rows)

                    class Batch:
                        def __init__(self, store):
                            self.store = store

                        def process(self, rows):
                            try:
                                self.store.commit(rows)
                                return "ok"
                            except OSError:
                                return "retry"
                '''),
            },
            '''
                import unittest
                from batch import Batch, Store

                class Public(unittest.TestCase):
                    def test_successful_batch(self):
                        store = Store(fail_at=1)
                        self.assertEqual(Batch(store).process(["a", "b"]), "retry")
                        self.assertEqual(store.rows, [])
            ''',
            '''
                import unittest
                from batch import Batch, Store

                class Hidden(unittest.TestCase):
                    def test_retry_does_not_duplicate_partial_rows(self):
                        store = Store(fail_at=1)
                        batch = Batch(store)
                        self.assertEqual(batch.process(["a", "b"]), "retry")
                        store.fail_at = None
                        self.assertEqual(batch.process(["a", "b"]), "ok")
                        self.assertEqual(store.rows, ["a", "b"])
            ''',
        ),
        spec(
            "tenant_feature_assignment", "cross-module",
            "A feature rollout assigns users without tenant scope. Preserve rollout identity at the targeting owner.",
            {
                "flags.py": code('''
                    def targeting_key(tenant, user):
                        return user

                    def enabled(tenant, user):
                        return targeting_key(tenant, user)
                '''),
            },
            {
                "flags.py": code('''
                    def targeting_key(tenant, user):
                        return f"{tenant}:{user}"

                    def enabled(tenant, user):
                        return targeting_key(tenant, user)
                '''),
            },
            '''
                import unittest
                from flags import enabled

                class Public(unittest.TestCase):
                    def test_key_is_stable_for_one_tenant(self):
                        self.assertEqual(enabled("acme", "u1"), "acme:u1")
            ''',
            '''
                import unittest
                from flags import enabled

                class Hidden(unittest.TestCase):
                    def test_tenant_is_part_of_rollout_identity(self):
                        self.assertNotEqual(enabled("acme", "u1"), enabled("globex", "u1"))
            ''',
        ),
        spec(
            "canonical_search_index", "cross-module",
            "A search query is normalized but indexed documents are not. Preserve canonicalization at both write and read owners.",
            {
                "index.py": code('''
                    import unicodedata

                    def normalize(value):
                        return unicodedata.normalize("NFKC", value).casefold().strip()

                    class Index:
                        def __init__(self):
                            self.values = {}

                        def add(self, value, document):
                            self.values.setdefault(value, []).append(document)

                        def search(self, query):
                            return list(self.values.get(normalize(query), []))
                '''),
            },
            {
                "index.py": code('''
                    import unicodedata

                    def normalize(value):
                        return unicodedata.normalize("NFKC", value).casefold().strip()

                    class Index:
                        def __init__(self):
                            self.values = {}

                        def add(self, value, document):
                            self.values.setdefault(normalize(value), []).append(document)

                        def search(self, query):
                            return list(self.values.get(normalize(query), []))
                '''),
            },
            '''
                import unittest
                from index import Index

                class Public(unittest.TestCase):
                    def test_ascii_search(self):
                        index = Index()
                        index.add("Ｆoo", "doc-1")
                        self.assertEqual(index.search("foo"), ["doc-1"])
            ''',
            '''
                import unittest
                from index import Index

                class Hidden(unittest.TestCase):
                    def test_write_and_read_share_canonical_form(self):
                        index = Index()
                        index.add("Ｆoo", "doc-1")
                        index.add(" Café ", "doc-2")
                        self.assertEqual(index.search("foo"), ["doc-1"])
                        self.assertEqual(index.search("café"), ["doc-2"])
            ''',
        ),
        spec(
            "cache_ttl_units", "single-module",
            "A cache interprets millisecond TTL as seconds. Preserve one time unit at the cache owner boundary.",
            {
                "ttl_cache.py": code('''
                    class Cache:
                        def __init__(self):
                            self.values = {}

                        def put(self, key, value, ttl_ms, now):
                            self.values[key] = (value, now + ttl_ms)

                        def get(self, key, now):
                            entry = self.values.get(key)
                            return None if entry is None or now >= entry[1] else entry[0]
                '''),
            },
            {
                "ttl_cache.py": code('''
                    class Cache:
                        def __init__(self):
                            self.values = {}

                        def put(self, key, value, ttl_ms, now):
                            self.values[key] = (value, now + ttl_ms / 1000)

                        def get(self, key, now):
                            entry = self.values.get(key)
                            return None if entry is None or now >= entry[1] else entry[0]
                '''),
            },
            '''
                import unittest
                from ttl_cache import Cache

                class Public(unittest.TestCase):
                    def test_immediate_read(self):
                        cache = Cache()
                        cache.put("k", "v", 1000, 10)
                        self.assertIsNone(cache.get("k", 11.1))
            ''',
            '''
                import unittest
                from ttl_cache import Cache

                class Hidden(unittest.TestCase):
                    def test_millisecond_expiry(self):
                        cache = Cache()
                        cache.put("k", "v", 1000, 10)
                        self.assertIsNone(cache.get("k", 11.1))
            ''',
        ),
        spec(
            "inventory_compare_and_swap", "integration",
            "A reservation reports success even when its versioned state transition is rejected. Preserve the store's compare-and-swap outcome.",
            {
                "inventory.py": code('''
                    class Store:
                        def __init__(self, quantity):
                            self.quantity = quantity
                            self.version = 1

                        def read(self):
                            return self.quantity, self.version

                        def compare_and_reserve(self, expected_version, amount):
                            if expected_version != self.version or amount > self.quantity:
                                return False
                            self.quantity -= amount
                            self.version += 1
                            return True

                    class Reservation:
                        def __init__(self, store):
                            self.store = store

                        def reserve(self, amount):
                            quantity, version = self.store.read()
                            if amount <= quantity:
                                self.store.compare_and_reserve(version, amount)
                                return True
                            return False
                '''),
            },
            {
                "inventory.py": code('''
                    class Store:
                        def __init__(self, quantity):
                            self.quantity = quantity
                            self.version = 1

                        def read(self):
                            return self.quantity, self.version

                        def compare_and_reserve(self, expected_version, amount):
                            if expected_version != self.version or amount > self.quantity:
                                return False
                            self.quantity -= amount
                            self.version += 1
                            return True

                    class Reservation:
                        def __init__(self, store):
                            self.store = store

                        def reserve(self, amount):
                            quantity, version = self.store.read()
                            if amount <= quantity:
                                return self.store.compare_and_reserve(version, amount)
                            return False
                '''),
            },
            '''
                import unittest
                from inventory import Reservation, Store

                class Public(unittest.TestCase):
                    def test_available_stock_is_reserved(self):
                        class RejectingStore(Store):
                            def compare_and_reserve(self, expected_version, amount):
                                return False

                        store = RejectingStore(3)
                        reservation = Reservation(store)
                        self.assertFalse(reservation.reserve(2))
                        self.assertEqual(store.quantity, 3)
            ''',
            '''
                import unittest
                from inventory import Reservation, Store

                class Hidden(unittest.TestCase):
                    def test_stale_version_is_not_reported_as_success(self):
                        class StaleReadStore(Store):
                            def read(self):
                                quantity, _ = super().read()
                                return quantity, 1

                        store = StaleReadStore(3)
                        store.version = 2
                        reservation = Reservation(store)
                        self.assertFalse(reservation.reserve(2))
                        self.assertEqual(store.quantity, 3)
            ''',
        ),
    ]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    result = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        result.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0" + bytes.fromhex(digest(path)))
    return result.hexdigest()


def write_tree(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(content.rstrip() + "\n", encoding="utf-8")


def materialize(output: Path, source_commit: str) -> None:
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing corpus: {output}")
    (output / "tasks").mkdir(parents=True)
    (output / "hidden").mkdir()
    records: list[dict[str, object]] = []
    tasks = make_tasks()
    if len(tasks) != 20 or len({task.task_id for task in tasks}) != len(tasks):
        raise AssertionError("v6 corpus must contain 20 unique tasks")
    for task in tasks:
        task_root = output / "tasks" / task.task_id
        hidden_root = output / "hidden" / task.task_id
        write_tree(task_root, task.source | {"task.md": task.description, "tests/test_public.py": task.public_test})
        write_tree(hidden_root, {"tests/test_hidden.py": task.hidden_test})
        records.append({
            "task_id": task.task_id,
            "stratum": task.stratum,
            "workspace_path": f"tasks/{task.task_id}",
            "hidden_root_path": f"hidden/{task.task_id}",
            "allowed_edit_paths": sorted(task.source),
            "public_command": PUBLIC_COMMAND,
            "hidden_command": PUBLIC_COMMAND,
            "workspace_tree_sha256": tree_digest(task_root),
            "hidden_tree_sha256": tree_digest(hidden_root),
            "causal_owner_candidates": sorted(task.source),
        })
    manifest = {
        "schema_version": 1,
        "source": {
            "name": "adam-synthetic-causal-state-boundaries-v6",
            "generator": "scripts/materialize_effect_corpus_v6.py",
            "generator_commit": source_commit,
        },
        "split": {
            "hidden_reference_available_only_to_scorer": True,
            "hidden_tests_are_injected_after_agent_exit": True,
            "rule": "public tests live in each task workspace; hidden tests are a separate scorer-only tree",
        },
        "tasks": records,
    }
    _ = (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--output", type=Path, required=True)
    _ = parser.add_argument("--generator-commit", required=True)
    arguments = cast(dict[str, object], vars(parser.parse_args()))
    materialize(cast(Path, arguments["output"]), cast(str, arguments["generator_commit"]))
    print(json.dumps({"output": str(arguments["output"]), "task_count": 20}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
