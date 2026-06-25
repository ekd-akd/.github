# Contributing

Org-wide defaults for every `ekd-akd` repository. A repo may override any of this with its
own `CONTRIBUTING.md`.

## Workflow

1. Branch off `main` (`feat/…`, `fix/…`, `chore/…`).
2. Make focused commits using **Conventional Commits** — the release tooling derives the
   next version from them:
   - `feat: …` → minor bump
   - `fix: …` → patch bump
   - `feat!: …` / `fix!: …` or a `BREAKING CHANGE:` footer → major bump
   - `chore:` / `docs:` / `refactor:` / `test:` → no release
3. Open a PR into `main`. CI (`ci.yml`) must be green — it's the required status check.
4. Squash-merge; the squash title should itself be a conventional-commit subject.

## Local checks

Match what CI runs so you fail fast locally:

- **Python:** `uvx ruff check .` and `uv run pytest -q` (if a `tests/` suite exists).
- **Node:** `pnpm lint && pnpm build && pnpm test` (or the npm/yarn equivalent).

## Deployment

Deploys happen from CI on push to `main` via the org's reusable `nuk-*` workflows — never
by hand on the controller. App config lives in `.nuklaut/deployment.yml`; secrets go in
GitHub Actions secrets (`APP_ENV` per repo, `ORG_*` for shared values), never in git.

## Don't commit secrets

No credentials, tokens, or `.env` files in git. If you leak one, rotate it immediately and
tell a maintainer — see [`SECURITY.md`](SECURITY.md).
