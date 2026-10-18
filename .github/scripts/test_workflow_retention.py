"""Repository-independent regression checks for deploy/retention wiring."""
import pathlib
import unittest


class WorkflowRetentionTests(unittest.TestCase):
    def setUp(self):
        self.workflows = pathlib.Path(__file__).resolve().parents[1] / "workflows"
        candidates = [self.workflows / name for name in (
            "main.yml", "deploy-cloud-run.yml", "deploy-firebase.yml", "deploy-notifications.yml")]
        self.deploy = next(path for path in candidates if path.exists()).read_text(encoding="utf-8")
        self.audit = (self.workflows / "retention-guard.yml").read_text(encoding="utf-8")

    def test_deployment_has_pre_and_post_retention_gates(self):
        command = "python3 .github/scripts/retention_guard.py "
        self.assertEqual(self.deploy.count(command), 2)
        release_markers = ("gcloud run deploy", "uses: google-github-actions/deploy-cloudrun@",
                           "deploy --only functions:", "npx --yes firebase-tools@15.22.1 deploy")
        release = min(self.deploy.index(m) for m in release_markers if m in self.deploy)
        self.assertLess(self.deploy.index(command), release)
        self.assertGreater(self.deploy.rindex(command), release)
        if "artifact_retention.py sync" in self.deploy:
            self.assertGreater(self.deploy.rindex(command), self.deploy.index("artifact_retention.py sync"))

    def test_guard_only_changes_do_not_redeploy(self):
        self.assertIn("paths-ignore:", self.deploy)
        self.assertIn("'.github/scripts/**'", self.deploy)
        self.assertTrue("'.github/workflows/retention-guard.yml'" in self.deploy or
                        "'.github/workflows/**'" in self.deploy)

    def test_prs_test_but_never_authenticate(self):
        self.assertIn("github.event_name != 'pull_request'", self.audit)
        self.assertNotIn("pull_request_target", self.audit)
        self.assertIn("needs: test", self.audit)
        self.assertIn("'test_*retention*.py'", self.audit)

    def test_manual_and_scheduled_checks_are_read_only_and_serialized(self):
        self.assertIn("workflow_dispatch:", self.audit)
        self.assertIn("schedule:", self.audit)
        self.assertIn("cancel-in-progress: false", self.audit)
        self.assertIn("timeout-minutes: 15", self.audit)
        self.assertNotIn("gcloud run deploy", self.audit)
        self.assertNotIn("firebase-tools", self.audit)
        self.assertNotIn("secrets versions destroy", self.audit)


class QueueRetentionTests(unittest.TestCase):
    def test_all_shared_workflows_preserve_pending_and_running_operations(self):
        workflows = pathlib.Path(__file__).resolve().parents[1] / "workflows"
        groups = set()
        for name in ["deploy-cloud-run.yml","retention-guard.yml","rollback-retained.yml","sync-retention.yml"]:
            text = (workflows / name).read_text(encoding="utf-8")
            block = text.split("concurrency:\n", 1)[1].split("\njobs:", 1)[0]
            self.assertIn("cancel-in-progress: false", block, name)
            self.assertIn("queue: max", block, name)
            groups.add(next(line.strip() for line in block.splitlines() if line.strip().startswith("group:")))
        self.assertEqual(len(groups), 1)


if __name__ == "__main__":
    unittest.main()
