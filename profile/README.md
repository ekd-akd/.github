# AKD

<!-- TODO(jona): replace this line with the real one-paragraph description of AKD.
     Everything below is accurate to the infra; this top blurb is the only placeholder. -->
> _AKD builds and runs its applications on a single self-hosted controller — every app is
> deployed the same way, behind one hardened edge, with shared data services._

## How we ship

Apps in this org deploy to a hardened **controller VPS** running Docker + Traefik + a
shared Postgres/Redis data stack, driven by the [`nuk`](https://github.com/astrojones/nuk)
CLI. Reusable CI/CD and release workflows live in
[`ekd-akd/.github`](https://github.com/ekd-akd/.github) — apps call them, they don't
duplicate them.

- **One edge.** Traefik terminates TLS (per-host Let's Encrypt over HTTP-01) and routes
  every app under `*.akd.jonaheidsick.de`.
- **Shared data.** A single Postgres (pgvector) + Redis stack; `nuk` provisions a per-app
  database/role and Redis ACL on request.
- **Deploy from CI.** Push to `main` → build → `nuk apply` on a persistent self-hosted
  runner. Per-PR preview environments at `pr-<n>.<app>.akd.jonaheidsick.de`.

## Conventions

- Minimum CI on every repo: `uses: ekd-akd/.github/.github/workflows/ci.yml@main`.
- Releases are conventional-commit driven (`release.yml`), no release PRs.
- App deploy manifests live at `.nuklaut/deployment.yml`.

---

*Internal org. Most repositories are private.*
