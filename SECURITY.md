# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

## Reporting a Vulnerability

If you discover a security vulnerability in Open Migration, **please do not open a public GitHub issue.**

Instead, report it privately:

1. Go to the [Security tab](https://github.com/open-migration/open-migration/security) on GitHub
2. Click **"Report a vulnerability"**
3. Provide a description, steps to reproduce, and potential impact

We will respond within **72 hours** and aim to release a patch within **7 days** for critical issues.

## Security Model

Open Migration is designed with a local-first, zero-trust model:

- **No network requests** — the core tool never sends your data anywhere
- **No cloud upload** — all processing happens on your machine
- **No accounts** — no login, no API keys required for core functionality
- **No telemetry** — zero usage tracking or analytics

The web UI (`omigrate serve`) binds to `127.0.0.1` only — it is not accessible from the network.

## Known Scope

The following are **not** considered security vulnerabilities:

- Processing malformed or adversarial export files resulting in unexpected output (not a crash/RCE)
- The HTML output containing the full text of your conversations (this is intentional)

The following **are** in scope:

- Remote code execution when parsing export files
- Path traversal vulnerabilities in file handling
- The web UI binding to non-localhost interfaces
- Data leakage to third-party services
