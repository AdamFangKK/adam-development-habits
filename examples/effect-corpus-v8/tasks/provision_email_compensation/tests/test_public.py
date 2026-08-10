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
