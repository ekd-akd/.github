# ekd-akd/.github — org-wide defaults

This special repo holds **org-wide GitHub defaults** for the `ekd-akd` organization:
reusable Actions workflows, a composite action, the public org profile, and the
default community-health files every repo inherits.

Adapted from [`astrojones/.github`](https://github.com/astrojones/.github), trimmed for
the AKD setup: **no ephemeral Hetzner runners** (we use persistent self-hosted runners,
not just-in-time VMs) and **no Hetzner/DNS-01 wildcard** (the controller issues per-host
certs over HTTP-01).

## Reusable workflows

Apps call these with `uses:` — they don't duplicate the logic.

| Workflow | Runs on | What it does |
|---|---|---|
| `ci.yml` | `ubuntu-latest` | Minimum CI baseline: lint + test for `python` \| `node` \| `static`. Steps self-skip when their tooling is absent. Meant to be the required status check on `main`. |
| `app-ci.yml` | `ubuntu-latest` | Build + push one or more images to `ghcr.io/ekd-akd/<repo>/<name>` from a JSON matrix. No runner needed — keeps image builds decoupled from the controller. |
| `release.yml` | `[self-hosted, akd]` (override to `["ubuntu-latest"]` on public repos) | Conventional-commit, no-PR release: derive next version, stamp version files, commit `[skip ci]`, tag + GitHub release. |
| `nuk-apply.yml` | `[self-hosted, akd]` | Deploy-only: pull already-built GHCR images into the shared daemon, then `nuk apply`. |
| `nuk-deploy.yml` | `[self-hosted, akd]` | Build + push + `nuk apply` in one shot (single-image apps). Writes per-app + org-shared env files. |
| `nuk-preview.yml` | `[self-hosted, akd]` | Per-PR ephemeral preview stack at `pr-<n>.<base_host>`, cap-enforced, with a sticky PR comment. `deploy` / `teardown` / `cleanup` modes. |
| `migration-shadow-check.yml` | `[self-hosted, akd]` | Pre-deploy safety gate: shadow-migrate a snapshot of the **live** controller Postgres and fail if rows are lost. |

`actions/calver/` is a pure composite action that computes a `YYYY.MM.N` CalVer from git tags.

## Runner model

The `nuk-*` and `migration-shadow-check` workflows run on the controller's **persistent
self-hosted runner**, labelled `[self-hosted, akd]` — they need the host docker socket,
the shared `nuk-postgres`, and the `/opt/nuklaut` bind-mount. Register **at least two**
runners with the `akd` label on the controller so deploys queue rather than block.

> The ephemeral Hetzner-VM runner pattern from `astrojones/.github`
> (`runner-up`/`down`/`sweep` + cloud-init) is intentionally **not** included: AKD has no
> Hetzner Cloud API token, and the persistent model is what we use. It can be added later
> if a burst-capacity need appears.

## Required org Actions secrets

Set these at **Org → Settings → Secrets and variables → Actions**; callers must use
`secrets: inherit`:

| Secret | Used by | Notes |
|---|---|---|
| `ORG_SENTRY_DSN` | `nuk-deploy.yml` | Optional. Written into `/opt/nuklaut/secrets/_shared.env` on every deploy. Edit the list in the workflow to add more. |
| `ORG_ANTHROPIC_API_KEY` | `nuk-deploy.yml` | Optional. Injected as `ANTHROPIC_API_KEY` into deployed apps. |

The deploy workflows authenticate to GHCR with the built-in `GITHUB_TOKEN` — no PAT.

## Consuming from an app repo

```yaml
# .github/workflows/ci.yml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  ci:
    uses: ekd-akd/.github/.github/workflows/ci.yml@main
    with:
      language: python   # python | node | static
```

```yaml
# .github/workflows/deploy.yml — build, push, and deploy on push to main
name: deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    uses: ekd-akd/.github/.github/workflows/nuk-deploy.yml@main
    secrets: inherit
```

App manifests live at `.nuklaut/deployment.yml` in the app repo (see the controller
README in `ekd-akd/vps` for the manifest shape).

## Community-health defaults

`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, the issue forms in
`.github/ISSUE_TEMPLATE/`, and `.github/PULL_REQUEST_TEMPLATE.md` are inherited by every
repo in the org that doesn't ship its own.
