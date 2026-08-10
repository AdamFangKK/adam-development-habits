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
