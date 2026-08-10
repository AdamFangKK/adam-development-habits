class BlobStore:
    def __init__(self, fail=False):
        self.fail = fail
        self.objects = {}

    def write(self, key, content):
        if self.fail:
            raise OSError("blob write failed")
        self.objects[key] = content
