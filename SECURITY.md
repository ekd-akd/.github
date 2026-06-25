# Security Policy

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue.

- Email **jona.heidsick@a-kd.net**, or
- Use **GitHub → Security → Report a vulnerability** (private advisory) on the affected repo.

Include what you found, how to reproduce it, and the impact you expect. We aim to
acknowledge within a few business days.

## Handling secrets

- Never commit credentials, tokens, or `.env` files. Per-app secrets live in GitHub Actions
  secrets (`APP_ENV`) and on the controller under `/opt/nuklaut/secrets/` (mode `0600`).
- If a secret is exposed, **rotate it immediately**, then purge it from history if needed.

## Supported versions

Only the latest `main` of each repository is supported. There are no backports.
