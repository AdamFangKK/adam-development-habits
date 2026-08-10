class Billing:
    def __init__(self):
        self.charges = []
        self.refunds = []

    def charge(self, user):
        self.charges.append(user)

    def refund(self, user):
        self.refunds.append(user)
