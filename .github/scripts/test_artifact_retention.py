import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import artifact_retention as r


A, B, C = ("sha256:" + char * 64 for char in "abc")
PACKAGE = "us-docker.pkg.dev/demo/gcr.io/app"


class RetentionTests(unittest.TestCase):
    def test_normalize_gcr(self):
        self.assertEqual(r.normalize("gcr.io/demo/app@" + A), (PACKAGE, A))

    def test_reject_tag_instead_of_digest(self):
        with self.assertRaises(ValueError):
            r.normalize(PACKAGE + ":latest")

    def test_choose_new_and_previous_active(self):
        self.assertEqual(r.choose(B, A, C, {A, B, C}), [B, A])

    def test_unchanged_deploy_preserves_history(self):
        self.assertEqual(r.choose(B, B, A, {A, B}), [B, A])

    def test_single_version_is_valid(self):
        self.assertEqual(r.choose(A, A, None, {A}), [A])

    def test_missing_historical_fails_closed(self):
        with self.assertRaises(ValueError):
            r.choose(B, A, None, {B})

    def test_index_dependencies_and_standalone_attestation_preserved(self):
        registry = object.__new__(r.Registry)
        registry.cache = {
            A: {"manifests": [{"digest": B}]},
            B: {},
            C: {"artifactType": "attestation", "subject": {"digest": B}},
        }
        self.assertEqual(registry.closure([A], {A, B, C}), {A, B, C})

    def test_sync_protects_before_retiring_tags_without_deleting_images(self):
        images = [
            {"package": PACKAGE, "version": A, "tags": ["cost-retain-active"]},
            {"package": PACKAGE, "version": B, "tags": []},
            {"package": PACKAGE, "version": C, "tags": ["cost-retain-previous",
                                                        "cost-retain-dependency-old"]},
        ]
        calls = []
        registry = object.__new__(r.Registry)
        registry.cache = {A: {}, B: {}, C: {}}
        with tempfile.TemporaryDirectory() as tmp:
            state = pathlib.Path(tmp) / "state.json"
            state.write_text(json.dumps({"target": ["demo", "us-central1", "app"],
                                         "package": PACKAGE, "digest": A}))
            with patch.object(r, "current", return_value=PACKAGE + "@" + B), \
                 patch.object(r, "cloud", return_value=images), \
                 patch.object(r, "Registry", return_value=registry), \
                 patch.object(registry, "check_permissions"), \
                 patch.object(registry, "set_tag", side_effect=lambda *a: calls.append(a)):
                r.sync("demo", "us-central1", "app", state)
        self.assertEqual(len(calls), 3)
        self.assertIn(("cost-retain-active", B, A), calls[:2])
        self.assertIn(("cost-retain-previous", A, C), calls[:2])
        self.assertEqual(calls[-1], ("cost-retain-dependency-old", B, C))

    def test_matching_tag_is_noop_without_delete_permission(self):
        registry = object.__new__(r.Registry)
        with patch.object(r.urllib.request, "urlopen") as urlopen:
            registry.set_tag("cost-retain-active", A, A)
            urlopen.assert_not_called()

    def test_existing_tag_uses_patch_not_delete(self):
        registry = object.__new__(r.Registry)
        registry.package, registry.token = PACKAGE, "unit-test-token"
        with patch.object(r.urllib.request, "urlopen") as urlopen, \
             patch.object(r.json, "load", return_value={}):
            registry.set_tag("cost-retain-active", B, A)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "PATCH")
        self.assertTrue(request.full_url.endswith("?updateMask=version"))
        self.assertTrue(json.loads(request.data)["version"].endswith(B))

    def test_tagged_other_revision_blocks_capture(self):
        svc = {"status": {"traffic": [
            {"revisionName": "active", "percent": 100},
            {"revisionName": "other", "tag": "preview"},
        ]}}
        with patch.object(r, "cloud", return_value=svc):
            with self.assertRaises(ValueError):
                r.current("demo", "us-central1", "app")

    def test_rollback_rejects_wrong_service_before_mutation(self):
        revision = {"metadata": {"labels": {"serving.knative.dev/service": "other"}}}
        with patch.object(r, "current", return_value=PACKAGE + "@" + A), \
             patch.object(r, "cloud", return_value=revision), \
             patch.object(r, "mutate") as mutate:
            with self.assertRaises(ValueError):
                r.rollback("demo", "us-central1", "app", "unused", "revision")
            mutate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
