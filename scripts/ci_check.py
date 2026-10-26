"""Delivery checks. These commands fail closed. They do not skip a gate."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHANGES = ROOT / "docs" / "changes"
WAIVERS = ROOT / "docs" / "security" / "waivers"
PLAYWRIGHT = ROOT / "tests" / "playwright"
PRODUCT = ROOT / "product.yaml"

REQUIRED_STEPS = [
    "issue",
    "change_pack",
    "design",
    "implementation",
    "new_playwright_tests",
    "snyk",
    "secret_scanning",
    "playwright",
    "deploy_dev",
    "deploy_test",
    "uat_approval",
    "deploy_staging",
    "deploy_preprod",
    "k6",
    "zap",
    "prod_approval",
    "deploy_prod",
]
ENVIRONMENTS = ["dev", "test", "uat", "staging", "preprod", "prod"]
PROTECTED_PREFIXES = ("infra/", ".github/workflows/")
PROTECTED_FILES = {
    "apps/api/app/auth.py",
    "apps/api/requirements.txt",
    "apps/web/package.json",
    "tests/playwright/package.json",
    "scripts/requirements.txt",
}
REQ_ID = re.compile(r"REQ-[A-Z0-9-]+")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
MAJOR_VERSION = re.compile(r"^[1-9]\d*\.0\.0$")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        fail(f"{path} must be a mapping")
    return data


def change_packs() -> list[tuple[Path, dict]]:
    packs = []
    if not CHANGES.exists():
        fail("docs/changes is missing")
    for path in sorted(CHANGES.glob("*/change.yaml")):
        if path.parent.name.startswith("_"):
            continue
        packs.append((path, load_yaml(path)))
    if not packs:
        fail("No change pack found under docs/changes")
    return packs


def require_text(data: dict, key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"{path} is missing {key}")
    return value


def check_change_pack() -> None:
    for path, data in change_packs():
        release_class = data.get("release_class")
        if release_class not in ("experiment", "major"):
            fail(f"{path} release_class must be experiment or major")
        version = require_text(data, "version", path)
        if not VERSION.match(version):
            fail(f"{path} version must be semver")
        if release_class == "experiment" and MAJOR_VERSION.match(version):
            fail(f"{path} an experiment cannot use a major version")
        if release_class == "major" and not MAJOR_VERSION.match(version):
            fail(f"{path} a major release must use a version x.0.0")
        if not isinstance(data.get("behavior_change"), bool):
            fail(f"{path} behavior_change must be true or false")
        issue = data.get("issue")
        if not isinstance(issue, (str, int)) or str(issue).strip() == "":
            fail(f"{path} issue is required")
        product = load_yaml(PRODUCT)
        if version != str(product.get("version")):
            fail(f"{path} version must match product.yaml")
        require_text(data, "title", path)
        require_text(data, "threats", path)
        require_text(data, "rollback", path)
        requirements = data.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            fail(f"{path} requirements must be a non-empty list")
        for requirement in requirements:
            if not isinstance(requirement, dict):
                fail(f"{path} each requirement must be a mapping")
            req_id = requirement.get("id")
            if not isinstance(req_id, str) or not REQ_ID.fullmatch(req_id):
                fail(f"{path} requirement id must look like REQ-1")
            if not str(requirement.get("statement", "")).strip():
                fail(f"{path} {req_id} is missing a statement")
            if not str(requirement.get("acceptance", "")).strip():
                fail(f"{path} {req_id} is missing acceptance")
        nfr = data.get("nfr")
        if not isinstance(nfr, dict):
            fail(f"{path} nfr is required")
        if not isinstance(nfr.get("p95_ms"), int) or nfr["p95_ms"] <= 0:
            fail(f"{path} nfr.p95_ms must be a positive integer")
        error_rate = nfr.get("error_rate")
        if not isinstance(error_rate, (int, float)) or not 0 <= float(error_rate) < 1:
            fail(f"{path} nfr.error_rate must be between 0 and 1")
        steps = data.get("required_steps")
        if not isinstance(steps, dict):
            fail(f"{path} required_steps is required")
        if list(steps) != REQUIRED_STEPS:
            fail(f"{path} required_steps must list every gate in order")
        for step, status in steps.items():
            if status not in ("pending", "passed", "not_applicable"):
                fail(f"{path} step {step} has an unknown status")
        approved = data.get("environments_approved")
        if not isinstance(approved, list) or any(item not in ENVIRONMENTS for item in approved):
            fail(f"{path} environments_approved has an unknown environment")
        deviations = data.get("deviations", [])
        if not isinstance(deviations, list):
            fail(f"{path} deviations must be a list")
        not_applicable = [step for step, status in steps.items() if status == "not_applicable"]
        if not_applicable and not deviations:
            fail(f"{path} not_applicable steps need an approved deviation")
        for deviation in deviations:
            if not isinstance(deviation, dict):
                fail(f"{path} each deviation must be a mapping")
            for key in ("id", "what", "rule", "why", "pipeline_steps_still_run", "approved_by"):
                if not str(deviation.get(key, "")).strip():
                    fail(f"{path} deviation is missing {key}")
        print(f"change pack ok: {path.relative_to(ROOT)}")


def playwright_titles() -> str:
    text = []
    for path in PLAYWRIGHT.rglob("*.ts"):
        text.append(path.read_text(encoding="utf-8"))
    return "\n".join(text)


def check_requirements() -> None:
    titles = playwright_titles()
    for path, data in change_packs():
        for requirement in data["requirements"]:
            req_id = requirement["id"]
            if req_id not in titles:
                fail(f"{req_id} from {path.name} has no Playwright title")
        if data["behavior_change"] and "@feature" not in titles:
            fail(f"{path} changes behavior and has no @feature Playwright test")
        print(f"requirements ok: {path.relative_to(ROOT)}")


def check_waivers() -> None:
    today = date.today()
    if not WAIVERS.exists():
        fail("docs/security/waivers is missing")
    found = False
    for path in sorted(WAIVERS.glob("*.yaml")):
        found = True
        data = load_yaml(path)
        for key in ("id", "finding_id", "severity", "reason", "approved_by"):
            if not str(data.get(key, "")).strip():
                fail(f"{path} is missing {key}")
        if data["severity"] not in ("critical", "high", "medium", "low"):
            fail(f"{path} severity is unknown")
        expires = data.get("expires_on")
        try:
            expiry = date.fromisoformat(str(expires))
        except ValueError:
            fail(f"{path} expires_on must be YYYY-MM-DD")
        if expiry < today:
            fail(f"{path} expired on {expiry.isoformat()}")
        print(f"waiver ok: {path.relative_to(ROOT)}")
    if not found:
        print("no waivers")


def git_changed_files() -> list[str] | None:
    if not (ROOT / ".git").exists():
        return None
    base = os.environ.get("GITHUB_BASE_REF")
    if base:
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base}...HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if diff.returncode == 0:
            return [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if head.returncode != 0:
        return None
    return None


def is_protected(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized in PROTECTED_FILES or normalized.startswith(PROTECTED_PREFIXES)


def check_protected_paths() -> None:
    changed = git_changed_files()
    if changed is None:
        changed = [
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts and "node_modules" not in path.parts
        ]
    protected = [path for path in changed if is_protected(path)]
    if not protected:
        print("no protected paths changed")
        return
    deviations = []
    for _, data in change_packs():
        deviations.extend(data.get("deviations", []))
    if not deviations:
        fail("Protected paths changed without an approved deviation: " + ", ".join(protected))
    print("protected paths have an approved deviation")


def release_lane() -> str:
    classes = {data["release_class"] for _, data in change_packs()}
    if "major" in classes:
        return "major"
    if classes == {"experiment"}:
        return "experiment"
    fail("Every change pack needs release_class experiment or major")
    return ""


def check_release_class() -> None:
    print(release_lane())


def check_workflows() -> None:
    workflow_dir = ROOT / ".github" / "workflows"
    if not workflow_dir.exists():
        fail(".github/workflows is missing")
    for path in sorted(workflow_dir.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        jobs = data.get("jobs", {})
        if not isinstance(jobs, dict):
            fail(f"{path} has no jobs")
        for name, job in jobs.items():
            if isinstance(job, dict) and "if" in job:
                fail(f"{path} job {name} has an if and can be skipped")
        print(f"workflow ok: {path.relative_to(ROOT)}")


def check_prod_gate() -> None:
    for path, data in change_packs():
        if "preprod" not in data.get("environments_approved", []):
            fail(f"{path} cannot promote to prod until preprod is in environments_approved")
    print("preprod evidence present")


def nft_env() -> None:
    _, data = change_packs()[-1]
    nfr = data["nfr"]
    print(f"P95_MS={nfr['p95_ms']}")
    print(f"ERROR_RATE={nfr['error_rate']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "change-pack",
            "requirements",
            "waivers",
            "protected-paths",
            "release-class",
            "prod-gate",
            "nft-env",
            "workflows",
        ],
    )
    args = parser.parse_args()
    {
        "change-pack": check_change_pack,
        "requirements": check_requirements,
        "waivers": check_waivers,
        "protected-paths": check_protected_paths,
        "release-class": check_release_class,
        "prod-gate": check_prod_gate,
        "nft-env": nft_env,
        "workflows": check_workflows,
    }[args.command]()


if __name__ == "__main__":
    main()
