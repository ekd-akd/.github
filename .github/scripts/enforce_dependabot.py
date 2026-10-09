#!/usr/bin/env python3
"""Open a PR adding .github/dependabot.yml to every org repo that lacks one.

dependabot.yml cannot be inherited from the org's .github repo, so it has to
exist in each repo. The ecosystems are derived from the manifests a repo
actually contains, so a Python service gets `uv` + `docker` + `github-actions`
and a Node service gets `npm` instead.

Usage: enforce_dependabot.py ORG [--dry-run]
Auth: `gh` must be authenticated (GH_TOKEN with repo access to the whole org).
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys

BRANCH = "chore/add-dependabot"
SKIP_REPOS = {".github", ".github-private"}
# Exact names only: Dependabot ignores e.g. docker-compose.job-template.yml.
COMPOSE_NAMES = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def render_config(paths: list[str]) -> str:
    """Return the dependabot.yml for a repo's file paths, or "" if nothing is updatable."""
    names = set(paths)
    updates: list[tuple[str, str]] = []
    for path in sorted(paths):
        if "node_modules/" in path:
            continue
        directory, _, name = path.rpartition("/")
        if name == "uv.lock" and f"{directory}/pyproject.toml".lstrip("/") in names:
            ecosystem = "uv"
        elif name == "package.json":
            ecosystem = "npm"
        elif name == "Dockerfile":
            ecosystem = "docker"
        elif name in COMPOSE_NAMES:
            ecosystem = "docker-compose"
        else:
            continue
        updates.append((ecosystem, f"/{directory}"))
    if any(p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")) for p in paths):
        updates.append(("github-actions", "/"))

    blocks = [
        f"  - package-ecosystem: {eco}\n"
        f"    directory: {directory}\n"
        "    schedule:\n"
        "      interval: weekly\n"
        "    groups:\n"
        f"      {eco}:\n"
        '        patterns: ["*"]\n'
        for eco, directory in dict.fromkeys(updates)
    ]
    return "version: 2\nupdates:\n" + "".join(blocks) if blocks else ""


def open_pr(repo: str, config: str) -> None:
    default_branch = gh("api", f"repos/{repo}", "--jq", ".default_branch").strip()
    base_sha = gh("api", f"repos/{repo}/git/ref/heads/{default_branch}", "--jq", ".object.sha").strip()
    gh("api", f"repos/{repo}/git/refs", "-f", f"ref=refs/heads/{BRANCH}", "-f", f"sha={base_sha}")
    gh(
        "api", f"repos/{repo}/contents/.github/dependabot.yml", "--method", "PUT",
        "-f", "message=chore: add dependabot config",
        "-f", f"content={base64.b64encode(config.encode()).decode()}",
        "-f", f"branch={BRANCH}",
    )  # fmt: skip
    ecosystems = sorted({line.split(": ")[1] for line in config.splitlines() if "package-ecosystem" in line})
    gh(
        "api", f"repos/{repo}/pulls",
        "-f", "title=chore: add dependabot config",
        "-f", f"head={BRANCH}",
        "-f", f"base={default_branch}",
        "-f", "body=Enables weekly Dependabot version updates for: " + ", ".join(ecosystems)
        + ".\n\nGenerated from this repo's manifests by ekd-akd/.github `enforce-dependabot`.",
    )  # fmt: skip


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("org")
    parser.add_argument("--dry-run", action="store_true", help="print configs, open no PRs")
    args = parser.parse_args()

    repos = json.loads(gh("repo", "list", args.org, "--no-archived", "--source", "--limit", "200", "--json", "name"))
    for name in sorted(r["name"] for r in repos):
        repo = f"{args.org}/{name}"
        if name in SKIP_REPOS:
            continue
        try:
            paths = json.loads(
                gh("api", f"repos/{repo}/git/trees/HEAD?recursive=1", "--jq", '[.tree[] | select(.type=="blob") | .path]')
            )
        except subprocess.CalledProcessError:
            print(f"- {repo}: empty or unreadable, skipping")
            continue
        if ".github/dependabot.yml" in paths or ".github/dependabot.yaml" in paths:
            print(f"✓ {repo}")
            continue
        config = render_config(paths)
        if not config:
            print(f"- {repo}: no updatable manifests, skipping")
            continue
        if args.dry_run:
            print(f"→ {repo} would get:\n{config}")
            continue
        try:
            open_pr(repo, config)
            print(f"→ {repo}: PR opened")
        except subprocess.CalledProcessError as exc:
            # Most likely the branch already exists from an earlier run; keep going.
            print(f"! {repo}: {exc.stderr.strip()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
