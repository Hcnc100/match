import unittest
from unittest.mock import patch
import retention_guard as guard
import artifact_retention as retention
from contextlib import ExitStack


class FakeClient:
    project = "test"

    def __init__(self, channel=None, release=None, versions=None, inventory=None):
        self.channel = channel or {}
        self.release = release or []
        self.versions = versions or []
        self.inventory = inventory or []

    def get(self, _):
        return self.channel

    def list(self, url, _):
        if "/releases?" in url:
            return self.release
        if "/versions?" in url:
            return self.versions
        return self.inventory


class GuardTests(unittest.TestCase):
    def client(self, previous_status="FINALIZED", limit=2):
        active = {"name": "sites/site/versions/a", "status": "FINALIZED"}
        return FakeClient(channel={"retainedReleaseCount": limit, "release": {"version": active}},
                          release=[{"version": active}, {"version": {"name": "sites/site/versions/b", "status": previous_status}}])

    def test_two_hosting_releases(self):
        result = guard.hosting(self.client(), "site")
        self.assertTrue(result["historicalAvailable"])
        self.assertEqual(result["usableVersions"], 2)

    def test_one_is_not_current_plus_previous(self):
        with self.assertRaises(ValueError):
            guard.hosting(self.client(limit=1), "site")

    def test_unlimited_hosting_rejected(self):
        with self.assertRaises(ValueError):
            guard.hosting(self.client(limit=2147483647), "site")

    def test_expired_history_not_reported_as_rollback(self):
        result = guard.hosting(self.client(previous_status="EXPIRED"), "site")
        self.assertFalse(result["historicalAvailable"])
        self.assertEqual(result["usableVersions"], 1)

    def test_no_deployment_is_valid(self):
        result = guard.hosting(FakeClient(channel={"retainedReleaseCount": 2}), "site")
        self.assertFalse(result["historicalAvailable"])

    def test_nonfinalized_active_rejected(self):
        client = self.client()
        client.channel["release"]["version"]["status"] = "EXPIRED"
        with self.assertRaises(ValueError):
            guard.hosting(client, "site")

    def test_active_missing_from_history_rejected(self):
        client = self.client()
        client.release = []
        with self.assertRaises(ValueError):
            guard.hosting(client, "site")

    def test_gc_grace_does_not_claim_strict_count(self):
        client = self.client()
        client.release.append({"version": {"name": "c", "status": "FINALIZED"}})
        self.assertTrue(guard.hosting(client, "site")["cleanupPending"])

    def secret_client(self, states, aliases=None):
        return FakeClient(inventory=[{"name": "projects/test/secrets/example", "versionAliases": aliases or {}}],
                          versions=[{"name": "projects/test/secrets/example/versions/" + str(i + 1), "state": state}
                                    for i, state in enumerate(states)])

    def test_two_secret_versions(self):
        result = guard.secrets(self.secret_client(["ENABLED", "ENABLED"]))
        self.assertEqual(result["enabledVersions"], 2)
        self.assertFalse(result["automaticDestruction"])

    def test_disabled_also_counts_toward_limit(self):
        with self.assertRaises(ValueError):
            guard.secrets(self.secret_client(["ENABLED", "DISABLED", "DISABLED"]))

    def test_destroyed_not_retained(self):
        self.assertEqual(guard.secrets(self.secret_client(["DESTROYED", "ENABLED", "ENABLED"]))["enabledVersions"], 2)

    def test_unknown_state_fails_closed(self):
        with self.assertRaises(ValueError):
            guard.secrets(self.secret_client(["PENDING"]))

    def test_alias_to_destroyed_rejected(self):
        with self.assertRaises(ValueError):
            guard.secrets(self.secret_client(["DESTROYED", "ENABLED"], {"stable": "1"}))

    def test_empty_secret_inventory(self):
        self.assertEqual(guard.secrets(FakeClient())["secretCount"], 0)

    def test_pagination_preserves_query(self):
        client = object.__new__(guard.Client)
        with patch.object(client, "get", side_effect=[{"items": [1], "nextPageToken": "a b"}, {"items": [2]}]) as mock:
            self.assertEqual(client.list("https://example.invalid/x?pageSize=100", "items"), [1, 2])
            self.assertIn("pageSize=100", mock.call_args.args[0])
            self.assertIn("pageToken=a+b", mock.call_args.args[0])

    def test_repeated_page_token_rejected(self):
        client = object.__new__(guard.Client)
        with patch.object(client, "get", return_value={"nextPageToken": "same"}):
            with self.assertRaises(ValueError):
                client.list("https://example.invalid/x", "items")

    def image_check(self, change=None):
        package = "us-docker.pkg.dev/test/repo/app"
        policy = {"cleanupPolicyDryRun": False, "cleanupPolicies": {
            "delete": {"action": "DELETE", "condition": {"tagState": "ANY", "olderThan": "86400s"}},
            "keep": {"action": "KEEP", "condition": {"tagState": "TAGGED", "tagPrefixes": ["cost-retain-"]}},
        }}
        inventory = [{"package": package, "version": "sha256:a", "tags": ["cost-retain-active"]},
                     {"package": package, "version": "sha256:b", "tags": ["cost-retain-previous"]}]
        if change:
            change(policy, inventory)
        with ExitStack() as stack:
            stack.enter_context(patch.object(guard, "cloud", return_value=policy))
            stack.enter_context(patch.object(retention, "current", return_value=package + "@sha256:a"))
            stack.enter_context(patch.object(retention, "cloud", return_value=inventory))
            registry = stack.enter_context(patch.object(retention, "Registry"))
            registry.return_value.closure.return_value = {"sha256:a", "sha256:b"}
            return guard.images("test", "us-central1", "app")

    def test_image_policy_and_two_roots(self):
        self.assertEqual(self.image_check()["applicationVersions"], 2)

    def test_image_simulation_fails(self):
        with self.assertRaises(ValueError):
            self.image_check(lambda p, _: p.update(cleanupPolicyDryRun=True))

    def test_missing_keep_rule_fails(self):
        with self.assertRaises(ValueError):
            self.image_check(lambda p, _: p["cleanupPolicies"].pop("keep"))

    def test_short_image_grace_fails(self):
        with self.assertRaises(ValueError):
            self.image_check(lambda p, _: p["cleanupPolicies"]["delete"]["condition"].update(olderThan="60s"))

    def test_active_tag_mismatch_fails(self):
        with self.assertRaises(ValueError):
            self.image_check(lambda _, i: i[0].update(tags=[]))

    def test_unrelated_protected_history_fails(self):
        with self.assertRaises(ValueError):
            self.image_check(lambda _, i: i.append({"package": i[0]["package"], "version": "sha256:c", "tags": ["cost-retain-stale"]}))


if __name__ == "__main__":
    unittest.main()
