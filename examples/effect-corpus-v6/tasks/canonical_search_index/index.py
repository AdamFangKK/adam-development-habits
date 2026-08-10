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
