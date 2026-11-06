"""Payload filesystem/integrity tests; fixtures contain no executable AI model."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from mjon_os.offline_payload import create_payload, initialize_model_store, validate_payload


class OfflinePayloadTests(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(tmp)
        self.runtime = self.root / "runtime"
        (self.runtime / "bin").mkdir(parents=True)
        (self.runtime / "bin/ollama").write_text("fixture, never execute")
        (self.runtime / "LICENSE").write_text("fixture license")
        (self.runtime / "lib/ollama").mkdir(parents=True)
        (self.runtime / "lib/ollama/LICENSE").write_text("fixture license")
        self.models = self.root / "models"
        (self.models / "blobs").mkdir(parents=True)
        blob = b"fixture model, not real weights"
        digest = hashlib.sha256(blob).hexdigest()
        (self.models / "blobs" / ("sha256-" + digest)).write_bytes(blob)
        manifest = self.models / "manifests/registry.ollama.ai/library/tiny/test"
        manifest.parent.mkdir(parents=True)
        reference = {"digest": "sha256:" + digest, "size": len(blob),
                     "mediaType": "application/vnd.ollama.image.model"}
        manifest.write_text(json.dumps({"config": reference, "layers": [reference,
            {**reference, "mediaType": "application/vnd.ollama.image.license"}]}))
        self.payload = self.root / "payload"
        create_payload(self.runtime, self.models, self.payload, model="tiny:test",
                       runtime_version="test-fixture", archive_sha256="0"*64)

    def test_tampered_weight_is_rejected(self):
        blob = next((self.payload / "models/blobs").iterdir())
        blob.write_text("tampered")
        with self.assertRaises(ValueError):
            validate_payload(self.payload)

    def test_existing_payload_is_never_overwritten(self):
        with self.assertRaises(FileExistsError):
            create_payload(self.runtime, self.models, self.payload, model="tiny:test",
                           runtime_version="test", archive_sha256="0"*64)

    @unittest.skipUnless(os.name == "posix", "Live ISO access uses POSIX permissions")
    def test_private_download_permissions_are_not_shipped_to_the_live_user(self):
        blob = next((self.models / "blobs").iterdir())
        blob.chmod(0o600)
        (self.models / "blobs").chmod(0o700)
        output = self.root / "readable-payload"
        create_payload(self.runtime, self.models, output, model="tiny:test",
                       runtime_version="test-fixture", archive_sha256="0"*64)
        self.assertEqual((output / "models/blobs").stat().st_mode & 0o777, 0o755)
        self.assertEqual((output / "models/blobs" / blob.name).stat().st_mode & 0o777, 0o644)
        self.assertEqual((output / "manifest.json").stat().st_mode & 0o777, 0o644)
        self.assertEqual(blob.stat().st_mode & 0o777, 0o600)

    def test_live_store_links_weights_and_keeps_private_writable_manifests(self):
        store = self.root / "user-store"
        try:
            self.assertTrue(initialize_model_store(self.payload, store))
        except OSError as exc:
            if exc.errno in (1, 13) or getattr(exc, "winerror", None) == 1314:
                self.skipTest("Host does not permit filesystem symlinks")
            raise
        self.assertFalse((store / "blobs").is_symlink())
        self.assertTrue(next((store / "blobs").iterdir()).is_symlink())
        self.assertFalse((store / "manifests").is_symlink())
        self.assertFalse(initialize_model_store(self.payload, store))
        self.assertTrue((store / "manifests/registry.ollama.ai/library/tiny/test").is_file())
        (store / "manifests/registry.ollama.ai/library/tiny/profile-alias").write_text("user profile")
        (store / "blobs/new-profile-config").write_text("new private config blob")
        validate_payload(self.payload)

    def test_versioned_manifests_are_copied_to_a_private_writable_store(self):
        versioned = self.models / "manifests-v2/ollama.com/library/tiny/test"
        versioned.parent.mkdir(parents=True)
        versioned.write_text("versioned fixture metadata")
        payload = self.root / "versioned-payload"
        create_payload(self.runtime, self.models, payload, model="tiny:test",
                       runtime_version="test-fixture", archive_sha256="0"*64)
        store = self.root / "versioned-store"
        initialize_model_store(payload, store)
        copied = store / "manifests-v2/ollama.com/library/tiny/test"
        self.assertFalse(copied.is_symlink())
        self.assertEqual(copied.read_text(), "versioned fixture metadata")
        copied.write_text("private user metadata")
        validate_payload(payload)

    def test_foreign_user_store_is_preserved(self):
        store = self.root / "user-store"
        store.mkdir()
        important = store / "personal.txt"
        important.write_text("keep")
        with self.assertRaises((ValueError, OSError)):
            initialize_model_store(self.payload, store)
        self.assertEqual(important.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
