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
