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
| `ci.yml` | `ubuntu-latest` (input `runs-on`, private AKD repos pass `["self-hosted", "akd"]`) | Minimum CI baseline: lint + test for `python` \| `node` \| `static`. Steps self-skip when their tooling is absent. Meant to be the required status check on `main`. |
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

### Private submodules

`ci.yml`, `app-ci.yml` and `nuk-deploy.yml` can check out **private git submodules**
into the caller's workspace. Two things opt a caller in:

- Input `submodules` — passed straight to `actions/checkout` (`'false'` | `'true'` |
  `'recursive'`). Defaults to `'false'`, so a caller that sets nothing keeps today's
  behaviour exactly.
- Secret `SUBMODULE_TOKEN` — a token that can read the private submodule repos.
  Set it as a **repo secret in the caller** (not an org secret) and expose it with
  `secrets: inherit`. A fine-grained PAT or a GitHub App installation token with
  **Contents: read-only** is enough; nothing broader is needed. `actions/checkout` uses a
  single `token` for the whole step, so this token authenticates **both** the caller
  repo's own fetch **and** the submodules. It must therefore read the submodule repo(s)
  and — when the caller repo is private — the caller repo itself; a public caller repo
  needs read on the submodule repo(s) only.

Both HTTPS and `git@github.com:` SSH URLs in `.gitmodules` work: `actions/checkout`
rewrites SSH URLs to HTTPS when no `ssh-key` is set, so the token is applied either way.
Prefer the **HTTPS** URL (`https://github.com/ekd-akd/<repo>.git`) — that is the form AP5
records submodule URLs in. The token just needs read access.

```yaml
# .github/workflows/ci.yml
jobs:
  ci:
    uses: ekd-akd/.github/.github/workflows/ci.yml@main
    secrets: inherit
    with:
      language: python
      submodules: 'true'   # 'recursive' to pull nested submodules as well
```

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    uses: ekd-akd/.github/.github/workflows/nuk-deploy.yml@main
    secrets: inherit
    with:
      submodules: 'true'
```

**Build context:** a `.dockerignore` can exclude the checked-out submodule (or the
Dockerfile may not `COPY` it), giving a green checkout but an image that lacks the
submodule. Ensure the build context includes the submodule when the image needs it.

Without `SUBMODULE_TOKEN` the checkout **fails on purpose**: `actions/checkout` then
falls back to the automatic `github.token`, which is scoped to the caller repo and
cannot read a private submodule repo. A caller that sets `submodules: 'true'` but never
provides a readable token gets a hard clone failure — a deliberate signal, not silent
misbehaviour.

### Private git dependencies (Python)

A Python repo can depend on a private ekd-akd repo as a git dependency, e.g.
`akd-auth = { git = "https://github.com/ekd-akd/akd-auth.git", tag = "v0.1.0" }` in
`[tool.uv.sources]`. `ci.yml` and `nuk-deploy.yml` detect this (`git = "https://github.com/ekd-akd/…"` in
`pyproject.toml` / `uv.lock`) and, only then, look for a read token. Source, first hit wins:

1. **Host file `/etc/nuklaut/secrets/private-deps-token`** (first non-blank line = the token). The self-hosted
   runners (`akd-runner-1/2`) run their jobs as root and mount `/etc/nuklaut` read-only, so every job on them sees
   this file. No GitHub secret is needed in any consuming repo. The file is delivered by hand on the box (see
   `ekd-akd/infra`, `docs/runner-private-deps.md`); nuk's `sopsFile` decrypts only into `/run/nuklaut` on the host,
   which the runner containers do not mount.
2. Secrets `ORG_PAT` / `SUBMODULE_TOKEN` (for GitHub-hosted runners or boxes without the file). Callers pass them with
   `secrets: inherit`. On the org's Free plan an org-level secret is not delivered to private repos (checked: it arrives
   empty), so this needs a repo-level secret in the consumer.

What each workflow does with the token:

- **`ci.yml`** sets git credentials for `github.com/ekd-akd/` through job-scoped `GIT_CONFIG_*` variables before
  `uv sync` runs. Nothing is written to `~/.gitconfig`, so it cannot outlive the job on the self-hosted runner.
  Private repos must call it with `runs-on: '["self-hosted", "akd"]'` to see the host file.
- **`ci.yml`, input `auth-registry: true`** (opt-in, default off) additionally clones `ekd-akd/oauth` (depth 1) with those
  credentials and exports `AKD_AUTH_REGISTRY` (path of `auth-registry.yaml`) for the test run, so a service can test its auth
  defaults against the registry (`akd_auth.registry`). It fails closed: no credentials, no clone, or an empty file fails the job.
- **`nuk-deploy.yml`** passes the token to `docker build` as BuildKit secret `github_token`. The Dockerfile reads it
  with `RUN --mount=type=secret,id=github_token` in the *same* `RUN` that runs `uv sync`, and must not persist it
  (no `git config --global`, no `ARG`/`ENV`); use `GIT_CONFIG_*` variables inside that one command.

Without a token, or in repos without such a dependency, the steps are skipped and behaviour is unchanged.
Dependabot runs get no org secrets and run on GitHub-hosted runners, so Dependabot PRs on repos with a private
dependency fail `uv sync`.

## Community-health defaults

`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, the issue forms in
`.github/ISSUE_TEMPLATE/`, and `.github/PULL_REQUEST_TEMPLATE.md` are inherited by every
repo in the org that doesn't ship its own.
