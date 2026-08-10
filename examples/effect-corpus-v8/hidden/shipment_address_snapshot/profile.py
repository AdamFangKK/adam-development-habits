class Profile:
    def __init__(self, address):
        self.address = dict(address)

    def update_city(self, city):
        self.address["city"] = city
