"""Synchronize active/previous image protection after a verified Cloud Run release.
No image deletion or IAM changes. Native cleanup must remain disabled until adoption.
"""
import argparse
import json
import pathlib
import subprocess
import urllib.request
import urllib.parse


PREFIX = "cost-retain-"


def cloud(*args):
    result = subprocess.run(
        ["gcloud", *args, "--format=json", "--quiet"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout or "null")


def mutate(*args):
    subprocess.run(["gcloud", *args, "--quiet"], check=True,
                   stdout=subprocess.DEVNULL)


def normalize(image):
    package, digest = image.rsplit("@", 1)
    if not digest.startswith("sha256:"):
        raise ValueError("Resolved digest required")
    if package.startswith("gcr.io/"):
        project, rest = package[len("gcr.io/"):].split("/", 1)
        package = f"us-docker.pkg.dev/{project}/gcr.io/{rest}"
    if "-docker.pkg.dev/" not in package:
        raise ValueError("Only reviewed Artifact Registry hosts are supported")
    return package, digest


def choose(active, before, previous, available):
    if active not in available:
        raise ValueError("Active digest is missing from registry")
    historical = before if before and before != active else previous
    if historical and historical not in available:
        raise ValueError("Historical digest missing; refusing tag removal")
    return [active] + ([historical] if historical and historical != active else [])


def current(project, region, service):
    svc = cloud("run", "services", "describe", service,
                f"--project={project}", f"--region={region}")
    routes = svc["status"].get("traffic", [])
    serving = [r for r in routes if r.get("percent", 0)]
    if len(serving) != 1 or serving[0].get("percent") != 100:
        raise ValueError("Split traffic requires manual retention review")
    active = serving[0]["revisionName"]
    if any(r.get("tag") and r.get("revisionName") != active for r in routes):
        raise ValueError("Another tagged revision must be reviewed")
    revision = cloud("run", "revisions", "describe", active,
                     f"--project={project}", f"--region={region}")
    if not any(c["type"] == "Ready" and c["status"] == "True"
               for c in revision["status"]["conditions"]):
        raise ValueError("Revision not ready")
    return revision["status"]["imageDigest"]


class Registry:
    def __init__(self, package):
        self.package = package
        self.token = subprocess.run(
            ["gcloud", "auth", "print-access-token", "--quiet"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        self.cache = {}

    def manifest(self, digest):
        if digest not in self.cache:
            host, name = self.package.split("/", 1)
            req = urllib.request.Request(
                f"https://{host}/v2/{name}/manifests/{digest}",
                headers={"Authorization": f"Bearer {self.token}", "Accept":
                         "application/vnd.oci.image.index.v1+json, "
                         "application/vnd.oci.image.manifest.v1+json, "
                         "application/vnd.docker.distribution.manifest.v2+json, "
                         "application/vnd.docker.distribution.manifest.list.v2+json"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                self.cache[digest] = json.load(response)
        return self.cache[digest]

    def check_permissions(self):
        host, project, repo, _ = self.package.split("/", 3)
        location = host.removesuffix("-docker.pkg.dev")
        resource = f"projects/{project}/locations/{location}/repositories/{repo}"
        required = {"artifactregistry.tags.create", "artifactregistry.tags.update"}
        req = urllib.request.Request(
            f"https://artifactregistry.googleapis.com/v1/{resource}:testIamPermissions",
            data=json.dumps({"permissions": sorted(required)}).encode(), method="POST",
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            granted = set(json.load(response).get("permissions", []))
        if not required.issubset(granted):
            raise PermissionError("CI lacks tag create/update; no IAM changes attempted")

    def set_tag(self, tag, digest, current=None):
        if current == digest:
            return
        host, project, repo, package = self.package.split("/", 3)
        location = host.removesuffix("-docker.pkg.dev")
        resource = (f"projects/{project}/locations/{location}/repositories/{repo}"
                    f"/packages/{urllib.parse.quote(package, safe='')}")
        body = {"version": f"{resource}/versions/{digest}"}
        if current is None:
            url = f"https://artifactregistry.googleapis.com/v1/{resource}/tags?tagId={tag}"
            method = "POST"
        else:
            body["name"] = f"{resource}/tags/{tag}"
            url = (f"https://artifactregistry.googleapis.com/v1/{resource}"
                   f"/tags/{tag}?updateMask=version")
            method = "PATCH"
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), method=method,
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            json.load(response)

    def closure(self, roots, available):
        kept = set()
        def visit(digest):
            if digest in kept:
                return
            if digest not in available:
                raise ValueError("Referenced OCI manifest missing")
            kept.add(digest)
            for child in self.manifest(digest).get("manifests", []):
                visit(child["digest"])
        for root in roots:
            visit(root)
        # Preserve standalone provenance whose subject is a retained image.
        for digest in available:
            manifest = self.manifest(digest)
            if manifest.get("subject", {}).get("digest") in kept:
                visit(digest)
        return kept


def sync(project, region, service, state):
    snapshot = json.loads(pathlib.Path(state).read_text(encoding="utf-8"))
    if [project, region, service] != snapshot["target"]:
        raise ValueError("Snapshot target mismatch")
    package, active = normalize(current(project, region, service))
    if package != snapshot["package"]:
        raise ValueError("Repository/package changed; manual review required")
    repo = "/".join(package.split("/")[:3])
    images = cloud("artifacts", "docker", "images", "list", repo, "--include-tags")
    images = [i for i in images if i["package"] == package]
    available = {i["version"] for i in images}
    old_previous = [i["version"] for i in images
                    if PREFIX + "previous" in i.get("tags", [])]
    if len(old_previous) > 1:
        raise ValueError("Ambiguous historical tag")
    roots = choose(active, snapshot["digest"],
                   old_previous[0] if old_previous else None, available)
    registry = Registry(package)
    registry.check_permissions()
    keep = registry.closure(roots, available)
    desired = {PREFIX + "active": roots[0]}
    if len(roots) == 2:
        desired[PREFIX + "previous"] = roots[1]
    for digest in keep - set(roots):
        desired[PREFIX + "dependency-" + digest.split(":")[1]] = digest
    if normalize(current(project, region, service)) != (package, active):
        raise ValueError("Concurrent deploy detected")
    # Protect first. A partial failure leaks storage, never removes live protection.
    current_tags = {tag: image["version"] for image in images
                    for tag in image.get("tags", [])}
    for tag, digest in desired.items():
        registry.set_tag(tag, digest, current_tags.get(tag))
    if normalize(current(project, region, service)) != (package, active):
        raise ValueError("Concurrent deploy detected before tag retirement")
    for image in images:
        for tag in image.get("tags", []):
            if tag.startswith(PREFIX) and tag not in desired:
                # Writer accounts can update tags but cannot delete them. Retarget
                # obsolete metadata to the active image so it no longer pins history.
                registry.set_tag(tag, active, image["version"])
    print(f"Protected {len(roots)} application version(s) and "
          f"{len(keep - set(roots))} OCI dependencies for {service}")


def rollback(project, region, service, state, revision_name):
    if not revision_name:
        raise ValueError("Explicit historical revision required")
    package, before = normalize(current(project, region, service))
    revision = cloud("run", "revisions", "describe", revision_name,
                     f"--project={project}", f"--region={region}")
    if revision["metadata"].get("labels", {}).get("serving.knative.dev/service") != service:
        raise ValueError("Revision belongs to another service")
    if not any(c["type"] == "Ready" and c["status"] == "True"
               for c in revision["status"]["conditions"]):
        raise ValueError("Historical revision not ready")
    target_package, target = normalize(revision["status"]["imageDigest"])
    if target_package != package:
        raise ValueError("Historical package mismatch")
    images = cloud("artifacts", "docker", "images", "list",
                   "/".join(package.split("/")[:3]), "--include-tags")
    previous = [i["version"] for i in images if i["package"] == package
                and PREFIX + "previous" in i.get("tags", [])]
    if previous != [target]:
        raise ValueError("Only the protected previous image may be selected")
    pathlib.Path(state).write_text(json.dumps({
        "target": [project, region, service], "package": package, "digest": before,
    }), encoding="utf-8")
    if normalize(current(project, region, service)) != (package, before):
        raise ValueError("Concurrent deploy detected before rollback")
    mutate("run", "services", "update-traffic", service,
           f"--project={project}", f"--region={region}",
           f"--to-revisions={revision_name}=100")
    sync(project, region, service, state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["capture", "sync", "rollback"])
    parser.add_argument("--revision")
    for name in ("project", "region", "service", "state"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.mode == "capture":
        package, digest = normalize(current(args.project, args.region, args.service))
        pathlib.Path(args.state).write_text(json.dumps({
            "target": [args.project, args.region, args.service],
            "package": package, "digest": digest,
        }), encoding="utf-8")
    elif args.mode == "sync":
        sync(args.project, args.region, args.service, args.state)
    else:
        rollback(args.project, args.region, args.service, args.state, args.revision)


if __name__ == "__main__":
    main()
