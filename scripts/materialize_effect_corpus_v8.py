#!/usr/bin/env python3
"""Materialize a fresh v8 multi-file causal-repair corpus."""

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import cast


PUBLIC_COMMAND = ["python3", "-m", "unittest", "discover", "-s", "tests"]
EXPECTED_STRATA = {"single-module": 6, "cross-module": 8, "integration": 6}


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
        spec("iso_week_year_rollover", "single-module", "A calendar key uses the Gregorian year for ISO week numbers at year boundaries.",
            {"calendar_key.py": code('''
                def week_key(day):
                    return day.strftime("%Y-W%V")
            ''')},
            {"calendar_key.py": code('''
                def week_key(day):
                    return day.strftime("%G-W%V")
            ''')},
            '''
                import unittest
                from datetime import date
                from calendar_key import week_key

                class Public(unittest.TestCase):
                    def test_january_day_can_belong_to_previous_iso_year(self):
                        self.assertEqual(week_key(date(2021, 1, 1)), "2020-W53")
            ''',
            '''
                import unittest
                from datetime import date
                from calendar_key import week_key

                class Hidden(unittest.TestCase):
                    def test_iso_year_can_differ_in_both_directions(self):
                        self.assertEqual(week_key(date(2018, 12, 31)), "2019-W01")
                        self.assertEqual(week_key(date(2020, 6, 15)), "2020-W25")
            '''),
        spec("csv_blank_cell_preservation", "single-module", "A CSV-like row parser drops blank cells that are significant to column alignment.",
            {"row_parser.py": code('''
                def parse_row(line):
                    return [cell.strip() for cell in line.split(",") if cell.strip()]
            ''')},
            {"row_parser.py": code('''
                def parse_row(line):
                    return [cell.strip() for cell in line.split(",")]
            ''')},
            '''
                import unittest
                from row_parser import parse_row

                class Public(unittest.TestCase):
                    def test_empty_middle_cell_is_preserved(self):
                        self.assertEqual(parse_row("a,,c"), ["a", "", "c"])
            ''',
            '''
                import unittest
                from row_parser import parse_row

                class Hidden(unittest.TestCase):
                    def test_trailing_and_whitespace_blanks_are_preserved(self):
                        self.assertEqual(parse_row(" x , ,z,"), ["x", "", "z", ""])
                        self.assertEqual(parse_row(""), [""])
            '''),
        spec("scope_token_boundary", "single-module", "A scope check treats a required permission as satisfied when it is only a substring of another scope.",
            {"scopes.py": code('''
                def has_scope(token, required):
                    return required in token.get("scope", "")
            ''')},
            {"scopes.py": code('''
                def has_scope(token, required):
                    return required in token.get("scope", "").split()
            ''')},
            '''
                import unittest
                from scopes import has_scope

                class Public(unittest.TestCase):
                    def test_scope_must_match_a_token_boundary(self):
                        self.assertFalse(has_scope({"scope": "bread write"}, "read"))
            ''',
            '''
                import unittest
                from scopes import has_scope

                class Hidden(unittest.TestCase):
                    def test_exact_scope_is_required(self):
                        self.assertTrue(has_scope({"scope": "read write"}, "read"))
                        self.assertFalse(has_scope({"scope": "read:all"}, "read"))
                        self.assertFalse(has_scope({}, "read"))
            '''),
        spec("expiry_at_deadline", "single-module", "An expiry helper keeps credentials valid at the exact deadline.",
            {"expiry.py": code('''
                def expired(now, issued_at, ttl):
                    return now > issued_at + ttl
            ''')},
            {"expiry.py": code('''
                def expired(now, issued_at, ttl):
                    return now >= issued_at + ttl
            ''')},
            '''
                import unittest
                from expiry import expired

                class Public(unittest.TestCase):
                    def test_deadline_is_already_expired(self):
                        self.assertTrue(expired(110, 100, 10))
            ''',
            '''
                import unittest
                from expiry import expired

                class Hidden(unittest.TestCase):
                    def test_before_after_and_zero_ttl(self):
                        self.assertFalse(expired(109, 100, 10))
                        self.assertTrue(expired(111, 100, 10))
                        self.assertTrue(expired(5, 5, 0))
            '''),
        spec("merge_patch_deletes_null", "single-module", "A merge-patch implementation ignores null values instead of deleting keys.",
            {"merge_patch.py": code('''
                def apply_patch(document, patch):
                    result = dict(document)
                    for key, value in patch.items():
                        if value is not None:
                            result[key] = value
                    return result
            ''')},
            {"merge_patch.py": code('''
                def apply_patch(document, patch):
                    result = dict(document)
                    for key, value in patch.items():
                        if value is None:
                            result.pop(key, None)
                        else:
                            result[key] = value
                    return result
            ''')},
            '''
                import unittest
                from merge_patch import apply_patch

                class Public(unittest.TestCase):
                    def test_null_removes_existing_key(self):
                        self.assertEqual(apply_patch({"name": "a", "tag": "old"}, {"tag": None}), {"name": "a"})
            ''',
            '''
                import unittest
                from merge_patch import apply_patch

                class Hidden(unittest.TestCase):
                    def test_delete_missing_and_update_existing_keys(self):
                        self.assertEqual(apply_patch({"a": 1}, {"missing": None}), {"a": 1})
                        self.assertEqual(apply_patch({"a": 1}, {"a": 2, "b": 3}), {"a": 2, "b": 3})
            '''),
        spec("checksum_field_boundaries", "single-module", "A checksum concatenates fields without boundaries and collides for different records.",
            {"checksums.py": code('''
                import hashlib

                def digest(fields):
                    payload = "".join(fields)
                    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
            ''')},
            {"checksums.py": code('''
                import hashlib

                def digest(fields):
                    payload = "".join(f"{len(field)}:{field}" for field in fields)
                    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
            ''')},
            '''
                import unittest
                from checksums import digest

                class Public(unittest.TestCase):
                    def test_boundaries_prevent_concatenation_collision(self):
                        self.assertNotEqual(digest(["ab", "c"]), digest(["a", "bc"]))
            ''',
            '''
                import unittest
                from checksums import digest

                class Hidden(unittest.TestCase):
                    def test_equal_records_match_and_order_still_matters(self):
                        self.assertEqual(digest(["x", ""]), digest(["x", ""]))
                        self.assertNotEqual(digest(["x", "y"]), digest(["y", "x"]))
            '''),
        spec("shipment_address_snapshot", "cross-module", "An order keeps a live reference to a profile address instead of the checkout-time snapshot.",
            {"profile.py": code('''
                class Profile:
                    def __init__(self, address):
                        self.address = dict(address)

                    def update_city(self, city):
                        self.address["city"] = city
            '''), "orders.py": code('''
                def create_order(profile):
                    return {"ship_to": profile.address}
            ''')},
            {"profile.py": code('''
                class Profile:
                    def __init__(self, address):
                        self.address = dict(address)

                    def update_city(self, city):
                        self.address["city"] = city
            '''), "orders.py": code('''
                def create_order(profile):
                    return {"ship_to": dict(profile.address)}
            ''')},
            '''
                import unittest
                from orders import create_order
                from profile import Profile

                class Public(unittest.TestCase):
                    def test_order_keeps_checkout_address(self):
                        profile = Profile({"city": "Old", "street": "1 Main"})
                        order = create_order(profile)
                        profile.update_city("New")
                        self.assertEqual(order["ship_to"]["city"], "Old")
            ''',
            '''
                import unittest
                from orders import create_order
                from profile import Profile

                class Hidden(unittest.TestCase):
                    def test_later_profile_mutations_do_not_rewrite_order(self):
                        profile = Profile({"city": "Old", "street": "1 Main"})
                        order = create_order(profile)
                        profile.address["street"] = "2 Main"
                        self.assertEqual(order["ship_to"], {"city": "Old", "street": "1 Main"})
            '''),
        spec("coupon_currency_guard", "cross-module", "A coupon lookup ignores currency and applies a discount in the wrong monetary unit.",
            {"coupons.py": code('''
                COUPONS = {"SAVE10": {"amount": 10, "currency": "USD"}}

                def discount_for(code, currency):
                    return COUPONS[code]["amount"]
            '''), "checkout.py": code('''
                from coupons import discount_for

                def total(subtotal, currency, coupon=None):
                    if coupon is None:
                        return subtotal
                    return subtotal - discount_for(coupon, currency)
            ''')},
            {"coupons.py": code('''
                COUPONS = {"SAVE10": {"amount": 10, "currency": "USD"}}

                def discount_for(code, currency):
                    coupon = COUPONS[code]
                    if coupon["currency"] != currency:
                        raise ValueError("coupon currency mismatch")
                    return coupon["amount"]
            '''), "checkout.py": code('''
                from coupons import discount_for

                def total(subtotal, currency, coupon=None):
                    if coupon is None:
                        return subtotal
                    return subtotal - discount_for(coupon, currency)
            ''')},
            '''
                import unittest
                from checkout import total

                class Public(unittest.TestCase):
                    def test_coupon_currency_must_match_order_currency(self):
                        with self.assertRaises(ValueError):
                            total(100, "EUR", "SAVE10")
            ''',
            '''
                import unittest
                from checkout import total

                class Hidden(unittest.TestCase):
                    def test_matching_coupon_and_no_coupon_paths(self):
                        self.assertEqual(total(100, "USD", "SAVE10"), 90)
                        self.assertEqual(total(100, "EUR"), 100)
            '''),
        spec("alert_dedupe_per_channel", "cross-module", "An alert dedupe key ignores delivery channel and suppresses a required second notification.",
            {"keys.py": code('''
                def dedupe_key(channel, event_id):
                    return event_id
            '''), "notifier.py": code('''
                from keys import dedupe_key

                class Notifier:
                    def __init__(self):
                        self.sent = set()
                        self.deliveries = []

                    def send(self, channel, event_id, message):
                        key = dedupe_key(channel, event_id)
                        if key in self.sent:
                            return False
                        self.sent.add(key)
                        self.deliveries.append((channel, message))
                        return True
            ''')},
            {"keys.py": code('''
                def dedupe_key(channel, event_id):
                    return f"{channel}:{event_id}"
            '''), "notifier.py": code('''
                from keys import dedupe_key

                class Notifier:
                    def __init__(self):
                        self.sent = set()
                        self.deliveries = []

                    def send(self, channel, event_id, message):
                        key = dedupe_key(channel, event_id)
                        if key in self.sent:
                            return False
                        self.sent.add(key)
                        self.deliveries.append((channel, message))
                        return True
            ''')},
            '''
                import unittest
                from notifier import Notifier

                class Public(unittest.TestCase):
                    def test_same_event_can_be_sent_on_two_channels(self):
                        notifier = Notifier()
                        self.assertTrue(notifier.send("email", "e1", "hello"))
                        self.assertTrue(notifier.send("sms", "e1", "hello"))
                        self.assertEqual(notifier.deliveries, [("email", "hello"), ("sms", "hello")])
            ''',
            '''
                import unittest
                from notifier import Notifier

                class Hidden(unittest.TestCase):
                    def test_duplicate_is_channel_specific(self):
                        notifier = Notifier()
                        self.assertTrue(notifier.send("email", "e1", "hello"))
                        self.assertFalse(notifier.send("email", "e1", "hello again"))
                        self.assertTrue(notifier.send("push", "e1", "hello"))
            '''),
        spec("email_domain_normalization", "cross-module", "An email canonicalizer lowercases the local part even though only domains are case-insensitive.",
            {"normalize.py": code('''
                def canonical_email(email):
                    return email.lower()
            '''), "accounts.py": code('''
                from normalize import canonical_email

                def account_key(email):
                    return canonical_email(email)
            ''')},
            {"normalize.py": code('''
                def canonical_email(email):
                    local, domain = email.rsplit("@", 1)
                    return local + "@" + domain.lower()
            '''), "accounts.py": code('''
                from normalize import canonical_email

                def account_key(email):
                    return canonical_email(email)
            ''')},
            '''
                import unittest
                from accounts import account_key

                class Public(unittest.TestCase):
                    def test_local_part_case_is_preserved(self):
                        self.assertEqual(account_key("Sales@EXAMPLE.COM"), "Sales@example.com")
            ''',
            '''
                import unittest
                from accounts import account_key

                class Hidden(unittest.TestCase):
                    def test_last_at_splits_address_and_domain_only_changes(self):
                        self.assertEqual(account_key("A@B@Example.ORG"), "A@B@example.org")
            '''),
        spec("webhook_raw_body_signature", "cross-module", "A webhook handler verifies a normalized JSON string instead of the exact signed raw body.",
            {"signer.py": code('''
                import hashlib
                import hmac

                SECRET = b"shared-secret"

                def signature(body):
                    return hmac.new(SECRET, body.encode("utf-8"), hashlib.sha256).hexdigest()

                def valid(body, sent_signature):
                    return hmac.compare_digest(signature(body), sent_signature)
            '''), "handler.py": code('''
                import json
                from signer import valid

                def accept(raw_body, sent_signature):
                    normalized = json.dumps(json.loads(raw_body), sort_keys=True, separators=(",", ":"))
                    return valid(normalized, sent_signature)
            ''')},
            {"signer.py": code('''
                import hashlib
                import hmac

                SECRET = b"shared-secret"

                def signature(body):
                    return hmac.new(SECRET, body.encode("utf-8"), hashlib.sha256).hexdigest()

                def valid(body, sent_signature):
                    return hmac.compare_digest(signature(body), sent_signature)
            '''), "handler.py": code('''
                from signer import valid

                def accept(raw_body, sent_signature):
                    return valid(raw_body, sent_signature)
            ''')},
            '''
                import unittest
                from handler import accept
                from signer import signature

                class Public(unittest.TestCase):
                    def test_signature_uses_exact_raw_body(self):
                        raw = '{"b":2, "a":1}'
                        self.assertTrue(accept(raw, signature(raw)))
            ''',
            '''
                import unittest
                from handler import accept
                from signer import signature

                class Hidden(unittest.TestCase):
                    def test_compact_body_and_wrong_signature(self):
                        raw = '{"a":1,"b":2}'
                        self.assertTrue(accept(raw, signature(raw)))
                        self.assertFalse(accept(raw, signature('{"b":2,"a":1}')))
            '''),
        spec("slot_overlap_half_open", "cross-module", "A scheduler treats adjacent half-open time slots as overlapping.",
            {"policy.py": code('''
                def overlaps(left, right):
                    return left[0] <= right[1] and right[0] <= left[1]
            '''), "scheduler.py": code('''
                from policy import overlaps

                def can_add(existing, candidate):
                    return all(not overlaps(slot, candidate) for slot in existing)
            ''')},
            {"policy.py": code('''
                def overlaps(left, right):
                    return left[0] < right[1] and right[0] < left[1]
            '''), "scheduler.py": code('''
                from policy import overlaps

                def can_add(existing, candidate):
                    return all(not overlaps(slot, candidate) for slot in existing)
            ''')},
            '''
                import unittest
                from scheduler import can_add

                class Public(unittest.TestCase):
                    def test_adjacent_slots_do_not_overlap(self):
                        self.assertTrue(can_add([(10, 11)], (11, 12)))
            ''',
            '''
                import unittest
                from scheduler import can_add

                class Hidden(unittest.TestCase):
                    def test_real_overlap_is_still_rejected(self):
                        self.assertFalse(can_add([(10, 12)], (11, 13)))
                        self.assertTrue(can_add([(10, 12), (14, 15)], (12, 14)))
            '''),
        spec("validation_errors_not_retryable", "cross-module", "A retry loop retries validation failures instead of surfacing them immediately.",
            {"errors.py": code('''
                def retryable(exc):
                    return True
            '''), "client.py": code('''
                from errors import retryable

                def submit(send, payload, attempts=2):
                    for _ in range(attempts):
                        try:
                            return send(payload)
                        except Exception as exc:
                            if not retryable(exc):
                                raise
                    return "deferred"
            ''')},
            {"errors.py": code('''
                def retryable(exc):
                    return isinstance(exc, TimeoutError)
            '''), "client.py": code('''
                from errors import retryable

                def submit(send, payload, attempts=2):
                    for _ in range(attempts):
                        try:
                            return send(payload)
                        except Exception as exc:
                            if not retryable(exc):
                                raise
                    return "deferred"
            ''')},
            '''
                import unittest
                from client import submit

                class Public(unittest.TestCase):
                    def test_validation_error_is_not_retried(self):
                        calls = []
                        def send(payload):
                            calls.append(payload)
                            raise ValueError("bad payload")
                        with self.assertRaises(ValueError):
                            submit(send, {"id": 1})
                        self.assertEqual(calls, [{"id": 1}])
            ''',
            '''
                import unittest
                from client import submit

                class Hidden(unittest.TestCase):
                    def test_timeout_retry_and_success_paths(self):
                        calls = []
                        def timeout(payload):
                            calls.append(payload)
                            raise TimeoutError("slow")
                        self.assertEqual(submit(timeout, {"id": 2}), "deferred")
                        self.assertEqual(len(calls), 2)
                        self.assertEqual(submit(lambda payload: "ok", {"id": 3}), "ok")
            '''),
        spec("ledger_chronological_export", "cross-module", "A ledger export sorts entries by account and loses chronological order.",
            {"serializer.py": code('''
                def serialize(entries):
                    return sorted(entries, key=lambda entry: entry["account"])
            '''), "ledger.py": code('''
                from serializer import serialize

                class Ledger:
                    def __init__(self):
                        self.entries = []

                    def append(self, entry):
                        self.entries.append(dict(entry))

                    def export(self):
                        return serialize(self.entries)
            ''')},
            {"serializer.py": code('''
                def serialize(entries):
                    return [dict(entry) for entry in entries]
            '''), "ledger.py": code('''
                from serializer import serialize

                class Ledger:
                    def __init__(self):
                        self.entries = []

                    def append(self, entry):
                        self.entries.append(dict(entry))

                    def export(self):
                        return serialize(self.entries)
            ''')},
            '''
                import unittest
                from ledger import Ledger

                class Public(unittest.TestCase):
                    def test_export_keeps_append_order(self):
                        ledger = Ledger()
                        ledger.append({"account": "b", "amount": 1})
                        ledger.append({"account": "a", "amount": 2})
                        self.assertEqual([entry["account"] for entry in ledger.export()], ["b", "a"])
            ''',
            '''
                import unittest
                from ledger import Ledger

                class Hidden(unittest.TestCase):
                    def test_export_returns_copies_in_chronological_order(self):
                        ledger = Ledger()
                        ledger.append({"account": "b", "amount": 1})
                        exported = ledger.export()
                        exported[0]["amount"] = 99
                        self.assertEqual(ledger.export()[0]["amount"], 1)
            '''),
        spec("provision_email_compensation", "integration", "A provisioning flow leaves an active account and captured charge after welcome email delivery fails.",
            {"accounts.py": code('''
                class Accounts:
                    def __init__(self):
                        self.active = set()

                    def create(self, user):
                        self.active.add(user)

                    def deactivate(self, user):
                        self.active.discard(user)
            '''), "billing.py": code('''
                class Billing:
                    def __init__(self):
                        self.charges = []
                        self.refunds = []

                    def charge(self, user):
                        self.charges.append(user)

                    def refund(self, user):
                        self.refunds.append(user)
            '''), "provision.py": code('''
                def provision(user, accounts, billing, mailer):
                    accounts.create(user)
                    billing.charge(user)
                    try:
                        mailer(user)
                    except Exception:
                        return "failed"
                    return "active"
            ''')},
            {"accounts.py": code('''
                class Accounts:
                    def __init__(self):
                        self.active = set()

                    def create(self, user):
                        self.active.add(user)

                    def deactivate(self, user):
                        self.active.discard(user)
            '''), "billing.py": code('''
                class Billing:
                    def __init__(self):
                        self.charges = []
                        self.refunds = []

                    def charge(self, user):
                        self.charges.append(user)

                    def refund(self, user):
                        self.refunds.append(user)
            '''), "provision.py": code('''
                def provision(user, accounts, billing, mailer):
                    accounts.create(user)
                    charged = False
                    try:
                        billing.charge(user)
                        charged = True
                        mailer(user)
                    except Exception:
                        if charged:
                            billing.refund(user)
                        accounts.deactivate(user)
                        return "failed"
                    return "active"
            ''')},
            '''
                import unittest
                from accounts import Accounts
                from billing import Billing
                from provision import provision

                def failing_mailer(user):
                    raise RuntimeError("mail unavailable")

                class Public(unittest.TestCase):
                    def test_mail_failure_compensates_prior_effects(self):
                        accounts = Accounts()
                        billing = Billing()
                        self.assertEqual(provision("u1", accounts, billing, failing_mailer), "failed")
                        self.assertNotIn("u1", accounts.active)
                        self.assertEqual(billing.refunds, ["u1"])
            ''',
            '''
                import unittest
                from accounts import Accounts
                from billing import Billing
                from provision import provision

                class BillingFailure(Billing):
                    def charge(self, user):
                        raise RuntimeError("processor down")

                class Hidden(unittest.TestCase):
                    def test_success_and_charge_failure_lifecycle(self):
                        accounts = Accounts()
                        billing = Billing()
                        self.assertEqual(provision("ok", accounts, billing, lambda user: None), "active")
                        self.assertIn("ok", accounts.active)
                        failed_accounts = Accounts()
                        failed_billing = BillingFailure()
                        self.assertEqual(provision("u2", failed_accounts, failed_billing, lambda user: None), "failed")
                        self.assertNotIn("u2", failed_accounts.active)
                        self.assertEqual(failed_billing.refunds, [])
            '''),
        spec("webhook_claim_before_effect", "integration", "A webhook receiver marks a nonce only after handling, so a partial failure can replay side effects.",
            {"nonces.py": code('''
                class Nonces:
                    def __init__(self):
                        self.used = set()

                    def seen(self, nonce):
                        return nonce in self.used

                    def mark(self, nonce):
                        self.used.add(nonce)

                    def claim(self, nonce):
                        if nonce in self.used:
                            return False
                        self.used.add(nonce)
                        return True
            '''), "receiver.py": code('''
                def receive(event, nonces, handler):
                    if nonces.seen(event["nonce"]):
                        return "duplicate"
                    try:
                        handler(event)
                    except Exception:
                        return "failed"
                    nonces.mark(event["nonce"])
                    return "ok"
            ''')},
            {"nonces.py": code('''
                class Nonces:
                    def __init__(self):
                        self.used = set()

                    def seen(self, nonce):
                        return nonce in self.used

                    def mark(self, nonce):
                        self.used.add(nonce)

                    def claim(self, nonce):
                        if nonce in self.used:
                            return False
                        self.used.add(nonce)
                        return True
            '''), "receiver.py": code('''
                def receive(event, nonces, handler):
                    if not nonces.claim(event["nonce"]):
                        return "duplicate"
                    try:
                        handler(event)
                    except Exception:
                        return "failed"
                    return "ok"
            ''')},
            '''
                import unittest
                from nonces import Nonces
                from receiver import receive

                class Public(unittest.TestCase):
                    def test_partial_failure_does_not_replay_effect(self):
                        effects = []
                        def handler(event):
                            effects.append(event["id"])
                            raise RuntimeError("after effect")
                        nonces = Nonces()
                        event = {"id": "evt1", "nonce": "n1"}
                        self.assertEqual(receive(event, nonces, handler), "failed")
                        self.assertEqual(receive(event, nonces, handler), "duplicate")
                        self.assertEqual(effects, ["evt1"])
            ''',
            '''
                import unittest
                from nonces import Nonces
                from receiver import receive

                class Hidden(unittest.TestCase):
                    def test_success_is_also_idempotent(self):
                        effects = []
                        def handler(event):
                            effects.append(event["id"])
                        nonces = Nonces()
                        event = {"id": "evt2", "nonce": "n2"}
                        self.assertEqual(receive(event, nonces, handler), "ok")
                        self.assertEqual(receive(event, nonces, handler), "duplicate")
                        self.assertEqual(effects, ["evt2"])
            '''),
        spec("transfer_destination_preflight", "integration", "A stock transfer removes source inventory before verifying destination capacity.",
            {"inventory.py": code('''
                class Inventory:
                    def __init__(self, stock, capacity):
                        self.stock = dict(stock)
                        self.capacity = capacity

                    def total(self):
                        return sum(self.stock.values())

                    def quantity(self, sku):
                        return self.stock.get(sku, 0)

                    def can_accept(self, amount):
                        return self.total() + amount <= self.capacity

                    def add(self, sku, amount):
                        if not self.can_accept(amount):
                            raise OverflowError("capacity")
                        self.stock[sku] = self.quantity(sku) + amount

                    def remove(self, sku, amount):
                        if self.quantity(sku) < amount:
                            raise ValueError("stock")
                        self.stock[sku] = self.quantity(sku) - amount
            '''), "transfer.py": code('''
                def transfer(source, destination, sku, amount):
                    source.remove(sku, amount)
                    destination.add(sku, amount)
                    return "moved"
            ''')},
            {"inventory.py": code('''
                class Inventory:
                    def __init__(self, stock, capacity):
                        self.stock = dict(stock)
                        self.capacity = capacity

                    def total(self):
                        return sum(self.stock.values())

                    def quantity(self, sku):
                        return self.stock.get(sku, 0)

                    def can_accept(self, amount):
                        return self.total() + amount <= self.capacity

                    def add(self, sku, amount):
                        if not self.can_accept(amount):
                            raise OverflowError("capacity")
                        self.stock[sku] = self.quantity(sku) + amount

                    def remove(self, sku, amount):
                        if self.quantity(sku) < amount:
                            raise ValueError("stock")
                        self.stock[sku] = self.quantity(sku) - amount
            '''), "transfer.py": code('''
                def transfer(source, destination, sku, amount):
                    if not destination.can_accept(amount):
                        raise OverflowError("capacity")
                    source.remove(sku, amount)
                    destination.add(sku, amount)
                    return "moved"
            ''')},
            '''
                import unittest
                from inventory import Inventory
                from transfer import transfer

                class Public(unittest.TestCase):
                    def test_rejected_transfer_keeps_source_stock(self):
                        source = Inventory({"widget": 5}, 10)
                        destination = Inventory({"other": 9}, 10)
                        with self.assertRaises(OverflowError):
                            transfer(source, destination, "widget", 2)
                        self.assertEqual(source.quantity("widget"), 5)
            ''',
            '''
                import unittest
                from inventory import Inventory
                from transfer import transfer

                class Hidden(unittest.TestCase):
                    def test_success_moves_exact_amount(self):
                        source = Inventory({"widget": 5}, 10)
                        destination = Inventory({}, 10)
                        self.assertEqual(transfer(source, destination, "widget", 3), "moved")
                        self.assertEqual(source.quantity("widget"), 2)
                        self.assertEqual(destination.quantity("widget"), 3)
            '''),
        spec("manifest_after_blob_write", "integration", "A publisher commits a manifest entry before the referenced blob write is durable.",
            {"blob_store.py": code('''
                class BlobStore:
                    def __init__(self, fail=False):
                        self.fail = fail
                        self.objects = {}

                    def write(self, key, content):
                        if self.fail:
                            raise OSError("blob write failed")
                        self.objects[key] = content
            '''), "manifest.py": code('''
                class Manifest:
                    def __init__(self):
                        self.latest = None

                    def point_to(self, key):
                        self.latest = key
            '''), "publisher.py": code('''
                def publish(version, content, blobs, manifest):
                    key = f"v{version}"
                    manifest.point_to(key)
                    blobs.write(key, content)
                    return key
            ''')},
            {"blob_store.py": code('''
                class BlobStore:
                    def __init__(self, fail=False):
                        self.fail = fail
                        self.objects = {}

                    def write(self, key, content):
                        if self.fail:
                            raise OSError("blob write failed")
                        self.objects[key] = content
            '''), "manifest.py": code('''
                class Manifest:
                    def __init__(self):
                        self.latest = None

                    def point_to(self, key):
                        self.latest = key
            '''), "publisher.py": code('''
                def publish(version, content, blobs, manifest):
                    key = f"v{version}"
                    blobs.write(key, content)
                    manifest.point_to(key)
                    return key
            ''')},
            '''
                import unittest
                from blob_store import BlobStore
                from manifest import Manifest
                from publisher import publish

                class Public(unittest.TestCase):
                    def test_failed_blob_write_does_not_advance_manifest(self):
                        manifest = Manifest()
                        with self.assertRaises(OSError):
                            publish(2, "payload", BlobStore(fail=True), manifest)
                        self.assertIsNone(manifest.latest)
            ''',
            '''
                import unittest
                from blob_store import BlobStore
                from manifest import Manifest
                from publisher import publish

                class Hidden(unittest.TestCase):
                    def test_success_writes_blob_then_manifest(self):
                        blobs = BlobStore()
                        manifest = Manifest()
                        self.assertEqual(publish(3, "payload", blobs, manifest), "v3")
                        self.assertEqual(blobs.objects["v3"], "payload")
                        self.assertEqual(manifest.latest, "v3")
            '''),
        spec("session_rotation_invalidates_old", "integration", "A session rotation issues a new token but keeps the prior token authorized.",
            {"tokens.py": code('''
                class Tokens:
                    def __init__(self):
                        self.current = {}
                        self.valid = set()

                    def issue(self, user, token):
                        self.current[user] = token
                        self.valid.add(token)

                    def verify(self, user, token):
                        return token in self.valid
            '''), "auth.py": code('''
                def login(tokens, user, token):
                    tokens.issue(user, token)
                    return token

                def authorized(tokens, user, token):
                    return tokens.verify(user, token)
            ''')},
            {"tokens.py": code('''
                class Tokens:
                    def __init__(self):
                        self.current = {}
                        self.valid = set()

                    def issue(self, user, token):
                        previous = self.current.get(user)
                        if previous is not None:
                            self.valid.discard(previous)
                        self.current[user] = token
                        self.valid.add(token)

                    def verify(self, user, token):
                        return self.current.get(user) == token and token in self.valid
            '''), "auth.py": code('''
                def login(tokens, user, token):
                    tokens.issue(user, token)
                    return token

                def authorized(tokens, user, token):
                    return tokens.verify(user, token)
            ''')},
            '''
                import unittest
                from auth import authorized, login
                from tokens import Tokens

                class Public(unittest.TestCase):
                    def test_rotating_token_invalidates_old_token(self):
                        tokens = Tokens()
                        login(tokens, "u1", "old")
                        login(tokens, "u1", "new")
                        self.assertFalse(authorized(tokens, "u1", "old"))
                        self.assertTrue(authorized(tokens, "u1", "new"))
            ''',
            '''
                import unittest
                from auth import authorized, login
                from tokens import Tokens

                class Hidden(unittest.TestCase):
                    def test_rotation_is_per_user(self):
                        tokens = Tokens()
                        login(tokens, "u1", "old")
                        login(tokens, "u2", "other")
                        login(tokens, "u1", "new")
                        self.assertFalse(authorized(tokens, "u1", "old"))
                        self.assertTrue(authorized(tokens, "u2", "other"))
            '''),
        spec("pipeline_lock_release_on_error", "integration", "A pipeline runner leaves its lock held when the guarded step raises.",
            {"lock.py": code('''
                class Lock:
                    def __init__(self):
                        self.held = False

                    def acquire(self):
                        if self.held:
                            raise RuntimeError("already held")
                        self.held = True

                    def release(self):
                        self.held = False
            '''), "runner.py": code('''
                def run(lock, step):
                    lock.acquire()
                    result = step()
                    lock.release()
                    return result
            ''')},
            {"lock.py": code('''
                class Lock:
                    def __init__(self):
                        self.held = False

                    def acquire(self):
                        if self.held:
                            raise RuntimeError("already held")
                        self.held = True

                    def release(self):
                        self.held = False
            '''), "runner.py": code('''
                def run(lock, step):
                    lock.acquire()
                    try:
                        return step()
                    finally:
                        lock.release()
            ''')},
            '''
                import unittest
                from lock import Lock
                from runner import run

                class Public(unittest.TestCase):
                    def test_exception_releases_lock(self):
                        lock = Lock()
                        def step():
                            raise RuntimeError("boom")
                        with self.assertRaises(RuntimeError):
                            run(lock, step)
                        self.assertFalse(lock.held)
            ''',
            '''
                import unittest
                from lock import Lock
                from runner import run

                class Hidden(unittest.TestCase):
                    def test_success_releases_and_allows_next_run(self):
                        lock = Lock()
                        self.assertEqual(run(lock, lambda: "ok"), "ok")
                        self.assertFalse(lock.held)
                        self.assertEqual(run(lock, lambda: "again"), "again")
            '''),
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
        raise ValueError("v8 corpus must contain 20 unique tasks")
    actual_strata = {stratum: sum(1 for task in tasks if task.stratum == stratum) for stratum in EXPECTED_STRATA}
    if actual_strata != EXPECTED_STRATA:
        raise ValueError(f"v8 corpus strata mismatch: {actual_strata}")
    unknown_strata = sorted({task.stratum for task in tasks} - set(EXPECTED_STRATA))
    if unknown_strata:
        raise ValueError(f"v8 corpus contains unknown strata: {unknown_strata}")
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
        "corpus_id": "effect-corpus-v8",
        "generated_by": "scripts/materialize_effect_corpus_v8.py",
        "task_count": len(tasks),
        "strata": EXPECTED_STRATA,
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
