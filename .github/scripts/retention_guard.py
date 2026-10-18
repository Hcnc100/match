"""Read-only deployment gates: two Hosting releases, protected images, <=2 secret versions.

No payload access, deletion, IAM changes, deploys or traffic updates. Native Hosting
and Artifact Registry perform cleanup; excess secrets fail closed for review.
"""
import argparse
import json
import shutil
import subprocess
import urllib.parse
import urllib.request


def cloud(*args):
    command = shutil.which("gcloud") or "gcloud"
    result = subprocess.run([command, *args, "--format=json", "--quiet"],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout or "null")


class Client:
    def __init__(self, project):
        self.project = project
        command = shutil.which("gcloud") or "gcloud"
        self.token = subprocess.run([command, "auth", "print-access-token"],
                                    check=True, capture_output=True, text=True).stdout.strip()

    def get(self, url):
        request = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + self.token,
            "x-goog-user-project": self.project,
        })
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)

    def list(self, url, field):
        result, seen = [], set()
        while True:
            response = self.get(url)
            result.extend(response.get(field, []))
            token = response.get("nextPageToken")
            if not token:
                return result
            if token in seen:
                raise ValueError("Repeated pagination token")
            seen.add(token)
            parts = urllib.parse.urlsplit(url)
            query = dict(urllib.parse.parse_qsl(parts.query))
            query["pageToken"] = token
            url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def hosting(client, site):
    base = "https://firebasehosting.googleapis.com/v1beta1/sites/" + site
    channel = client.get(base + "/channels/live")
    # Runtime readback after GC proved 1 retained only current, despite ambiguous
    # API wording about 'previous releases'. Two TOTAL is the tested configuration.
    if channel.get("retainedReleaseCount") != 2:
        raise ValueError("Hosting must retain two releases, not one")
    active = channel.get("release", {}).get("version", {})
    if active and active.get("status") != "FINALIZED":
        raise ValueError("Hosting active version is not finalized")
    releases = client.list(base + "/channels/live/releases?pageSize=100", "releases")
    usable = {r["version"]["name"] for r in releases
              if r.get("version", {}).get("status") == "FINALIZED"}
    if active and active["name"] not in usable:
        raise ValueError("Hosting active release absent from history")
    # GC is asynchronous: a transient third release isn't evidence of lost policy.
    return {"site": site, "retainedReleaseCount": 2, "usableVersions": len(usable),
            "historicalAvailable": len(usable - {active.get("name")}) > 0,
            "cleanupPending": len(usable) > 2}


def secrets(client):
    base = "https://secretmanager.googleapis.com/v1/projects/" + client.project + "/secrets"
    inventory = client.list(base + "?pageSize=100", "secrets")
    enabled = 0
    for secret in inventory:
        versions = client.list("https://secretmanager.googleapis.com/v1/" +
                               secret["name"] + "/versions?pageSize=100", "versions")
        if any(v.get("state") not in {"ENABLED", "DISABLED", "DESTROYED"} for v in versions):
            raise ValueError("Unknown secret version state; manual review required")
        retained = [v for v in versions if v["state"] != "DESTROYED"]
        if len(retained) > 2:
            raise ValueError("Secret has more than two retained versions: " + secret["name"])
        by_number = {v["name"].rsplit("/", 1)[1]: v for v in retained}
        for number in secret.get("versionAliases", {}).values():
            if str(number) not in by_number:
                raise ValueError("Secret alias targets missing/destroyed version")
        enabled += sum(v["state"] == "ENABLED" for v in retained)
    return {"project": client.project, "secretCount": len(inventory),
            "enabledVersions": enabled, "automaticDestruction": False}


def images(project, region, service):
    # Shared, already-tested active/previous synchronization implementation.
    import artifact_retention as retention
    package, active = retention.normalize(retention.current(project, region, service))
    host, owner, repo, package_name = package.split("/", 3)
    location = host.removesuffix("-docker.pkg.dev")
    policy = cloud("artifacts", "repositories", "describe", repo,
                   "--project=" + owner, "--location=" + location)
    if policy.get("cleanupPolicyDryRun", False):
        raise ValueError("Artifact cleanup is still in simulation")
    policies = list(policy.get("cleanupPolicies", {}).values())
    deleting = [p for p in policies if p.get("action") == "DELETE" and
                any(package_name.startswith(x) for x in
                    p.get("condition", {}).get("packageNamePrefixes", [""]))]
    if not deleting:
        raise ValueError("No delete policy covers deployed package")
    for p in deleting:
        condition = p.get("condition", {})
        if condition.get("tagState") != "ANY" or float(condition.get("olderThan", "0s").removesuffix("s")) < 86400:
            raise ValueError("Delete policy lacks reviewed 24-hour grace")
    if not any(p.get("action") == "KEEP" and
               p.get("condition", {}).get("tagState") == "TAGGED" and
               "cost-retain-" in p.get("condition", {}).get("tagPrefixes", []) and
               any(package_name.startswith(x) for x in p.get("condition", {}).get("packageNamePrefixes", [""]))
               for p in policies):
        raise ValueError("Missing keep policy for protection tags")
    inventory = retention.cloud("artifacts", "docker", "images", "list",
                                "/".join(package.split("/")[:3]), "--include-tags")
    inventory = [i for i in inventory if i["package"] == package]
    protected = {i["version"] for i in inventory
                 if any(t.startswith(retention.PREFIX) for t in i.get("tags", []))}
    active_tags = [i["version"] for i in inventory if "cost-retain-active" in i.get("tags", [])]
    previous = [i["version"] for i in inventory if "cost-retain-previous" in i.get("tags", [])]
    if active_tags != [active] or len(previous) > 1 or (previous and previous[0] == active):
        raise ValueError("Active/previous tags inconsistent")
    roots = [active] + previous
    available = {i["version"] for i in inventory}
    expected = retention.Registry(package).closure(roots, available)
    if protected != expected:
        raise ValueError("Protected digests differ from active/previous OCI closure")
    if retention.normalize(retention.current(project, region, service)) != (package, active):
        raise ValueError("Concurrent deployment during verification")
    return {"service": service, "applicationVersions": len(roots),
            "ociDependencies": len(expected - set(roots)),
            "unprotectedAwaitingCleanup": len(available - expected), "graceHours": 24}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--hosting-site", action="append", default=[])
    parser.add_argument("--secrets", action="store_true")
    parser.add_argument("--service")
    parser.add_argument("--region", default="us-central1")
    args = parser.parse_args()
    if not (args.hosting_site or args.secrets or args.service):
        parser.error("At least one resource check is required")
    client = Client(args.project) if args.hosting_site or args.secrets else None
    result = {"project": args.project}
    if args.hosting_site:
        result["hosting"] = [hosting(client, site) for site in args.hosting_site]
    if args.secrets:
        result["secrets"] = secrets(client)
    if args.service:
        result["images"] = images(args.project, args.region, args.service)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
