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
