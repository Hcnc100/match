# Retention gates

Native Hosting is configured for TWO retained releases (current + previous); runtime verification showed that 1 expired all previous content. Existing EXPIRED versions cannot be reported as rollback-ready. The next successful distinct deployment will create a usable predecessor.

Native Artifact Registry cleanup protects the actual active/previous application digests and their OCI dependency/provenance closure, with a 24-hour grace. Caches and metadata are not extra application versions. Do not deploy or roll back outside the coordinated workflows without syncing protection.

retention_guard.py is read-only. It verifies policy activation, tags, OCI closure, Hosting retention/history, and <=2 ENABLED or DISABLED versions per secret. It never accesses payloads, destroys versions, changes IAM or traffic. A third secret version FAILS the deployment gate and the weekly/manual audit; it is not silently deleted. Review consumers/rollback before manual pruning. Automatic destructive secret cleanup is deliberately NOT claimed or installed: latest references can hide the actual version already loaded in running instances.

The audit runs on matching default-branch changes, manually and weekly. Pull requests run 38 unit tests without cloud credentials; authenticated audits reuse existing deploy identities and concurrency. New IAM is never granted by these checks. GitHub sends failures according to the user's Actions notification settings; there is no separate notification bot.

Deployment gates run before and after release. Native cleanup is asynchronous: transient extra records are reported, not treated as a strict instantaneous two-record limit. No rebuild/deploy is triggered by guard-only changes.
