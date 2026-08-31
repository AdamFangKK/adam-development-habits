def evaluate(address, new_city):
    saved = dict(address)
    address['city'] = new_city
    return (saved['city'], address['city'])
